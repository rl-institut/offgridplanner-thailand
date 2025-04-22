# Pre- and post-processing for the grid and supply optimization
import json
from io import StringIO

import pandas as pd
from django.shortcuts import get_object_or_404

from offgridplanner.optimization.models import Nodes
from offgridplanner.optimization.supply.demand_estimation import get_demand_timeseries
from offgridplanner.optimization.supply.solar_potential import (
    get_dc_feed_in_sync_db_query,
)
from offgridplanner.projects.models import Project


class OptimizationDataHandler:
    def __init__(self, proj_id):
        self.project = get_object_or_404(Project, id=proj_id)
        self.energy_system_dict = self.project.energysystemdesign.to_nested_dict()
        self.supply_components = self.energy_system_dict.keys()
        self.grid_design_dict = self.project.griddesign.to_nested_dict()
        self.grid_components = self.grid_design_dict.keys()


class PreProcessor:
    """
    Replaces the previous class BaseOptimizer by calculating values needed for the optimization. Used to create
    jsons sent to the actual optimizer / simulation server
    """

    def __init__(self, proj_id):
        self.project = get_object_or_404(Project, id=proj_id)
        self.options = self.project.options
        self.tax = 0
        self.wacc = self.project.interest_rate / 100
        self.project_lifetime = self.project.lifetime
        self.crf = (self.wacc * (1 + self.wacc) ** self.project_lifetime) / (
            (1 + self.wacc) ** self.project_lifetime - 1
        )
        self.demand = self.collect_project_demand()
        self.energy_system_dict = self.project.energysystemdesign.to_nested_dict()
        self.supply_components = self.energy_system_dict.keys()
        self.grid_design_dict = self.project.griddesign.to_nested_dict()
        self.grid_components = self.grid_design_dict.keys()

    @staticmethod
    def annualize(n_days, value):
        return value / n_days * 365 if value is not None else 0

    def capex_multi_investment(self, capex_0, component_lifetime):
        """
        Calculates the equivalent CAPEX for components
        with lifetime less than the self.project lifetime.

        """
        # convert the string type into the float type for both inputs
        capex_0 = float(capex_0)
        component_lifetime = float(component_lifetime)
        if self.project_lifetime == component_lifetime:
            number_of_investments = 1
        else:
            number_of_investments = int(
                round(self.project_lifetime / component_lifetime + 0.5),
            )
        first_time_investment = capex_0 * (1 + self.tax)
        capex = first_time_investment
        for count_of_replacements in range(1, number_of_investments):
            if count_of_replacements * component_lifetime != self.project_lifetime:
                capex += first_time_investment / (
                    (1 + self.wacc) ** (count_of_replacements * component_lifetime)
                )
        # Subtraction of component value at end of life with last replacement (= number_of_investments - 1)
        # This part calculates the salvage costs
        if number_of_investments * component_lifetime > self.project_lifetime:
            last_investment = first_time_investment / (
                (1 + self.wacc) ** ((number_of_investments - 1) * component_lifetime)
            )
            linear_depreciation_last_investment = last_investment / component_lifetime
            capex = capex - linear_depreciation_last_investment * (
                number_of_investments * component_lifetime - self.project_lifetime
            ) / ((1 + self.wacc) ** self.project_lifetime)
        return capex

    def epc(self, capex, opex, lifetime):
        epc = self.annualize(
            self.project.n_days,
            self.crf
            * self.capex_multi_investment(
                capex_0=capex,
                component_lifetime=lifetime,
            )
            + opex,
        )

        return epc

    def collect_project_demand(self):
        """
        Check if the user has ticked the demand estimation box. If so, calculate the demand from the project nodes,
        else get the demand from the uploaded timeseries
        Returns:
            pd.DataFrame
        """
        if self.options.do_demand_estimation:
            demand_full_year = get_demand_timeseries(
                self.project.nodes, self.project.customdemand
            ).sum(axis=1)

            demand = demand_full_year.iloc[: (self.project.n_days * 24)]
        else:
            uploaded_data = self.project.customdemand.uploaded_data
            demand = pd.read_json(StringIO(uploaded_data))["demand"]
            # # TODO error is thrown for annual total consumption if full year demand is not defined - tbd fix
            # if self.n_days == 365:
            #     self.demand_full_year = self.demand
        return demand

    def get_site_coordinates(self):
        # TODO do currently default coords get set if the user uploads a timeseries instead of selecting consumers?
        #  There should be an input about the project site instead
        default_coords = (9.055158, 7.497112)
        nodes_qs = Nodes.objects.filter(project=self.project)
        if nodes_qs.exists():
            nodes = nodes_qs.get().df
            if not nodes[nodes["consumer_type"] == "power_house"].empty:
                lat, lon = nodes[nodes["consumer_type"] == "power_house"][
                    "latitude",
                    "longitude",
                ].to_list()
            else:
                lat, lon = nodes[["latitude", "longitude"]].mean().to_list()
        else:
            lat, lon = default_coords

        return lat, lon

    def replace_capex_with_epc(self, nested_dict, components):
        """
        Replaces the parameters "capex", "opex" and "lifetime" inside a nested dictionary with "epc" for all components
        specified in components.
        Parameters:
            nested_dict (dict): Nested dictionary from a NestedModel object
            components (list): List of strings with the component names
        Returns:
            dict: Edited dict with the epc values
        """
        if set(components).issubset(self.supply_components):
            for component in components:
                capex = nested_dict[component]["parameters"]["capex"]
                opex = nested_dict[component]["parameters"]["opex"]
                lifetime = nested_dict[component]["parameters"]["lifetime"]
                # add periodical costs to dict
                nested_dict[component]["parameters"]["epc"] = self.epc(
                    capex, opex, lifetime
                )
                # delete parameters that are no longer needed for the optimization (reduce size of the json)
                del nested_dict[component]["parameters"]["capex"]
                del nested_dict[component]["parameters"]["opex"]
                del nested_dict[component]["parameters"]["lifetime"]

        elif set(components).issubset(self.grid_components):
            for component in components:
                capex = nested_dict[component]["capex"]
                opex = 0
                lifetime = nested_dict[component]["lifetime"]
                # add periodical costs to dict
                nested_dict[component]["epc"] = self.epc(capex, opex, lifetime)
                # delete parameters that are no longer needed for the optimization (reduce size of the json)
                del nested_dict[component]["lifetime"]

        else:
            raise ValueError(
                "Components found neither in grid nor energy system models"
            )

        return nested_dict

    def collect_supply_opt_json_data(self):
        """
        Dumps the necessary data for the supply optimization into a single json object to be sent to the simulation server
        Returns:
             json: Json data containing oemof component parameters and necessary timeseries
        """
        lat, lon = self.get_site_coordinates()
        # TODO fix date to actual start_date
        # self.start_datetime = pd.to_datetime(self.project_dict["start_date"]).to_pydatetime()
        # start_datetime hardcoded as only 2022 pv and demand data is available
        start_datetime = pd.to_datetime("2022").to_pydatetime()
        dt_index = pd.date_range(
            start_datetime,
            start_datetime + pd.to_timedelta(self.project.n_days, unit="D"),
            freq="h",
            inclusive="left",
        )

        solar_potential = get_dc_feed_in_sync_db_query(
            lat,
            lon,
            dt_index,
        )

        sequences = {
            "index": self.demand.index.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
            "demand": self.demand.to_numpy().tolist(),
            "solar_potential": solar_potential.to_numpy().tolist(),
        }
        energy_system_design = self.energy_system_dict

        # calculate periodical costs of components out of input capex, opex and lifetime
        energy_system_design = self.replace_capex_with_epc(
            energy_system_design,
            ["battery", "diesel_genset", "inverter", "rectifier", "pv"],
        )
        supply_opt_json = json.dumps(
            {"sequences": sequences, "energy_system_design": energy_system_design}
        )

        return supply_opt_json

    def collect_grid_opt_json_data(self):
        # calculate periodical costs of components out of input capex, opex and lifetime

        grid_design = self.replace_capex_with_epc(
            self.grid_design_dict, ["distribution_cable", "connection_cable", "pole"]
        )
        grid_design["mg"]["epc"] = self.epc(
            self.grid_design_dict["mg"]["connection_cost"], 0, self.project.lifetime
        )

        grid_opt_json = json.dumps(
            {
                "nodes": self.project.nodes.df.to_json(),
                "grid_design": grid_design,
                "yearly_demand": self.demand.sum(),
            }
        )
        return grid_opt_json
