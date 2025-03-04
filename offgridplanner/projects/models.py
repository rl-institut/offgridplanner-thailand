import datetime
from collections import defaultdict
from io import StringIO

import pandas as pd
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.forms.models import model_to_dict


def default_start_date():
    current_year = datetime.datetime.now().year
    return datetime.datetime(current_year - 1, 1, 1)

class Options(models.Model):
    email_notification = models.BooleanField(default=False)
    do_demand_estimation = models.BooleanField(default=True)
    do_grid_optimization = models.BooleanField(default=True)
    do_es_design_optimization = models.BooleanField(default=True)


class Project(models.Model):
    def __str__(self):
        return f"Project {self.id}: {self.name}"

    # id = models.PositiveSmallIntegerField(db_index=True)
    name = models.CharField(max_length=51, null=True, blank=True)
    description = models.CharField(max_length=201, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    interest_rate = models.FloatField(validators=[MinValueValidator(0.0)], blank=False)
    lifetime = models.PositiveSmallIntegerField(
        default=25,
        validators=[MinValueValidator(1), MaxValueValidator(35)],
    )
    start_date = models.DateTimeField(default=default_start_date)
    temporal_resolution = models.PositiveSmallIntegerField(default=1)
    n_days = models.PositiveSmallIntegerField(default=365)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
    )
    options = models.ForeignKey(
        Options,
        on_delete=models.SET_NULL,
        null=True,
    )

    def export(self):
        """
        Parameters
        ----------
        ...
        Returns
        -------
        A dict with the parameters describing a scenario model
        """
        dm = model_to_dict(self, exclude=["id", "user", "options"])
        if self.options:
            dm["options_data"] = model_to_dict(self.options, exclude=["id"])
        # add nodes
        # add customdemand
        return dm


class CustomDemand(models.Model):
    # Corresponds to class Demand in tier_spatial planning, removed fields id (obsolete), use_custom_demand and use_custom_shares
    # (one or both of them should just be None in database if not used), and household_option (not sure what it is used for)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    very_low = models.FloatField(default=0.663)
    low = models.FloatField(default=0.215)
    middle = models.FloatField(default=0.076)
    high = models.FloatField(default=0.031)
    very_high = models.FloatField(default=0.015)
    annual_total_consumption = models.FloatField(blank=True, null=True)
    annual_peak_consumption = models.FloatField(blank=True, null=True)

    @property
    def calibration_option(self):
        if self.annual_total_consumption is None and self.annual_peak_consumption is None:
            return None

        calibration_option = "annual_total_consumption" if self.annual_total_consumption is not None else "annual_peak_consumption"
        return calibration_option


class Nodes(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    data = models.JSONField(null=True)

    @property
    def df(self):
        return pd.read_json(StringIO(self.data))

    def filter_consumers(self, consumer_type):
        """
        Parameters:
            consumer_type (str): One of "household", "enterprise", "public_service"
        """
        nodes = self.df
        consumer_type_df = nodes[
            (nodes['consumer_type'] == consumer_type)
            & (nodes['is_connected'] == True)
            ]
        return consumer_type_df

    @property
    def counts(self):
        counts = self.df.groupby(['consumer_type', 'consumer_detail']).size()
        return counts

    @property
    def have_custom_machinery(self):
        enterprises = self.df[self.df.consumer_type == "enterprise"]
        machinery = enterprises.groupby(['consumer_type', 'consumer_detail']).agg({'custom_specification': ';'.join}).custom_specification.loc["enterprise"]
        machinery.replace(";", "")
        if not machinery.eq("").all():
            return True
        else:
            return False

class Links(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    data = models.JSONField(null=True)

    @property
    def df(self):
        return pd.read_json(StringIO(self.data))

class GridDesign(models.Model):

    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    distribution_cable_lifetime = models.PositiveSmallIntegerField(default=25)
    distribution_cable_capex = models.FloatField(default=10)
    distribution_cable_max_length = models.FloatField(default=50)
    connection_cable_lifetime = models.PositiveSmallIntegerField(default=25)
    connection_cable_capex = models.FloatField(default=4)
    connection_cable_max_length = models.FloatField(default=20)
    pole_lifetime = models.PositiveSmallIntegerField(default=25)
    pole_capex = models.FloatField(default=800)
    pole_max_n_connections = models.PositiveSmallIntegerField(default=5)
    mg_connection_cost = models.FloatField(default=140)
    include_shs = models.BooleanField(default=True)
    shs_max_grid_cost = models.FloatField(default=0.6, blank=True, null=True)


class Energysystemdesign(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    battery_settings_is_selected = models.IntegerField(db_column='battery__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_settings_design = models.IntegerField(db_column='battery__settings__design', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_nominal_capacity = models.FloatField(db_column='battery__parameters__nominal_capacity', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_lifetime = models.PositiveIntegerField(db_column='battery__parameters__lifetime', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_capex = models.FloatField(db_column='battery__parameters__capex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_opex = models.FloatField(db_column='battery__parameters__opex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_soc_min = models.FloatField(db_column='battery__parameters__soc_min', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_soc_max = models.FloatField(db_column='battery__parameters__soc_max', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_c_rate_in = models.FloatField(db_column='battery__parameters__c_rate_in', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_c_rate_out = models.FloatField(db_column='battery__parameters__c_rate_out', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    battery_parameters_efficiency = models.FloatField(db_column='battery__parameters__efficiency', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_settings_is_selected = models.IntegerField(db_column='diesel_genset__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_settings_design = models.IntegerField(db_column='diesel_genset__settings__design', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_nominal_capacity = models.FloatField(db_column='diesel_genset__parameters__nominal_capacity', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_lifetime = models.PositiveIntegerField(db_column='diesel_genset__parameters__lifetime', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_capex = models.FloatField(db_column='diesel_genset__parameters__capex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_opex = models.FloatField(db_column='diesel_genset__parameters__opex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_variable_cost = models.FloatField(db_column='diesel_genset__parameters__variable_cost', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_fuel_cost = models.FloatField(db_column='diesel_genset__parameters__fuel_cost', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_fuel_lhv = models.FloatField(db_column='diesel_genset__parameters__fuel_lhv', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_min_load = models.FloatField(db_column='diesel_genset__parameters__min_load', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_max_load = models.FloatField(db_column='diesel_genset__parameters__max_load', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_min_efficiency = models.FloatField(db_column='diesel_genset__parameters__min_efficiency', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    diesel_genset_parameters_max_efficiency = models.FloatField(db_column='diesel_genset__parameters__max_efficiency', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_settings_is_selected = models.IntegerField(db_column='inverter__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_settings_design = models.IntegerField(db_column='inverter__settings__design', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_parameters_nominal_capacity = models.FloatField(db_column='inverter__parameters__nominal_capacity', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_parameters_lifetime = models.PositiveIntegerField(db_column='inverter__parameters__lifetime', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_parameters_capex = models.FloatField(db_column='inverter__parameters__capex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_parameters_opex = models.FloatField(db_column='inverter__parameters__opex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    inverter_parameters_efficiency = models.FloatField(db_column='inverter__parameters__efficiency', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_settings_is_selected = models.IntegerField(db_column='pv__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_settings_design = models.IntegerField(db_column='pv__settings__design', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_parameters_nominal_capacity = models.FloatField(db_column='pv__parameters__nominal_capacity', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_parameters_lifetime = models.PositiveIntegerField(db_column='pv__parameters__lifetime', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_parameters_capex = models.FloatField(db_column='pv__parameters__capex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    pv_parameters_opex = models.FloatField(db_column='pv__parameters__opex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_settings_is_selected = models.IntegerField(db_column='rectifier__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_settings_design = models.IntegerField(db_column='rectifier__settings__design', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_parameters_nominal_capacity = models.FloatField(db_column='rectifier__parameters__nominal_capacity', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_parameters_lifetime = models.PositiveIntegerField(db_column='rectifier__parameters__lifetime', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_parameters_capex = models.FloatField(db_column='rectifier__parameters__capex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_parameters_opex = models.FloatField(db_column='rectifier__parameters__opex', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    rectifier_parameters_efficiency = models.FloatField(db_column='rectifier__parameters__efficiency', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    shortage_settings_is_selected = models.FloatField(db_column='shortage__settings__is_selected', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    shortage_parameters_max_shortage_total = models.FloatField(db_column='shortage__parameters__max_shortage_total', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    shortage_parameters_max_shortage_timestep = models.FloatField(db_column='shortage__parameters__max_shortage_timestep', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.
    shortage_parameters_shortage_penalty_cost = models.FloatField(db_column='shortage__parameters__shortage_penalty_cost', blank=True, null=True)  # Field renamed because it contained more than one '_' in a row.

    def to_nested_dict(self):
        nested_dict = lambda: defaultdict(nested_dict)
        data = nested_dict()

        for field in self._meta.fields:
            if field.db_column is not None:
                value = getattr(self, field.name)
                parts = field.db_column.split("__")

                d = data
                for part in parts[:-1]:  # Traverse the dictionary except the last key
                    d = d[part]
                d[parts[-1]] = value  # Set the final value

        return data


class WeatherData(models.Model):
    dt = models.DateTimeField()
    lat = models.FloatField()
    lon = models.FloatField()
    wind_speed = models.FloatField(null=True, blank=True)
    temp_air = models.FloatField(null=True, blank=True)
    ghi = models.FloatField(null=True, blank=True)
    dni = models.FloatField(null=True, blank=True)
    dhi = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('dt', 'lat', 'lon')

    def __str__(self):
        return f"WeatherData({self.dt}, {self.lat}, {self.lon})"


class Simulation(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    task_id = models.CharField(max_length=80, null=True, blank=True)
    status = models.CharField(max_length=25, default="not yet started")

class Results(models.Model):
    # TODO potentially remove redundant fields that can just be calculated on the fly (e.g. upfront investment)
    simulation = models.OneToOneField(Simulation, on_delete=models.CASCADE, null=True)
    n_consumers = models.PositiveSmallIntegerField(null=True, blank=True)
    n_shs_consumers = models.PositiveSmallIntegerField(null=True, blank=True)
    n_poles = models.PositiveSmallIntegerField(null=True, blank=True)
    n_distribution_links = models.PositiveSmallIntegerField(null=True, blank=True)
    n_connection_links = models.PositiveSmallIntegerField(null=True, blank=True)
    length_distribution_cable = models.PositiveSmallIntegerField(null=True, blank=True)
    average_length_distribution_cable = models.FloatField(null=True, blank=True)
    length_connection_cable = models.PositiveSmallIntegerField(null=True, blank=True)
    average_length_connection_cable = models.FloatField(null=True, blank=True)
    cost_grid = models.PositiveIntegerField(null=True, blank=True)
    cost_shs = models.PositiveIntegerField(null=True, blank=True)
    lcoe = models.PositiveIntegerField(null=True, blank=True)
    res = models.FloatField(null=True, blank=True)
    shortage_total = models.FloatField(null=True, blank=True)
    surplus_rate = models.FloatField(null=True, blank=True)
    cost_renewable_assets = models.FloatField(null=True, blank=True)
    cost_non_renewable_assets = models.FloatField(null=True, blank=True)
    cost_fuel = models.FloatField(null=True, blank=True)
    pv_capacity = models.FloatField(null=True, blank=True)
    battery_capacity = models.FloatField(null=True, blank=True)
    inverter_capacity = models.FloatField(null=True, blank=True)
    rectifier_capacity = models.FloatField(null=True, blank=True)
    diesel_genset_capacity = models.FloatField(null=True, blank=True)
    peak_demand = models.FloatField(null=True, blank=True)
    surplus = models.FloatField(null=True, blank=True)
    fuel_to_diesel_genset = models.FloatField(null=True, blank=True)
    diesel_genset_to_rectifier = models.FloatField(null=True, blank=True)
    diesel_genset_to_demand = models.FloatField(null=True, blank=True)
    rectifier_to_dc_bus = models.FloatField(null=True, blank=True)
    pv_to_dc_bus = models.FloatField(null=True, blank=True)
    battery_to_dc_bus = models.FloatField(null=True, blank=True)
    dc_bus_to_battery = models.FloatField(null=True, blank=True)
    dc_bus_to_inverter = models.FloatField(null=True, blank=True)
    dc_bus_to_surplus = models.FloatField(null=True, blank=True)
    inverter_to_demand = models.FloatField(null=True, blank=True)
    time_grid_design = models.FloatField(null=True, blank=True)
    time_energy_system_design = models.FloatField(null=True, blank=True)
    time = models.FloatField(null=True, blank=True)
    co2_savings = models.FloatField(null=True, blank=True)
    max_voltage_drop = models.FloatField(null=True, blank=True)
    infeasible = models.PositiveSmallIntegerField(null=True, blank=True)
    average_annual_demand_per_consumer = models.FloatField(null=True, blank=True)
    total_annual_consumption = models.FloatField(null=True, blank=True)
    upfront_invest_grid = models.FloatField(null=True, blank=True)
    upfront_invest_diesel_gen = models.FloatField(null=True, blank=True)
    upfront_invest_inverter = models.FloatField(null=True, blank=True)
    upfront_invest_rectifier = models.FloatField(null=True, blank=True)
    upfront_invest_battery = models.FloatField(null=True, blank=True)
    upfront_invest_pv = models.FloatField(null=True, blank=True)
    co2_emissions = models.FloatField(null=True, blank=True)
    fuel_consumption = models.FloatField(null=True, blank=True)
    base_load = models.FloatField(null=True, blank=True)
    max_shortage = models.FloatField(null=True, blank=True)
    epc_total = models.FloatField(null=True, blank=True)
    epc_pv = models.FloatField(null=True, blank=True)
    epc_diesel_genset = models.FloatField(null=True, blank=True)
    epc_inverter = models.FloatField(null=True, blank=True)
    epc_rectifier = models.FloatField(null=True, blank=True)
    epc_battery = models.FloatField(null=True, blank=True)
