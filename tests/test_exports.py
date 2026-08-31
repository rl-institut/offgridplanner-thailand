import json
from pathlib import Path

import pandas as pd
import pytest
from reportlab.platypus import Paragraph
from reportlab.platypus import Spacer

from config.settings.base import EXAMPLE_PROJECT_PATH
from offgridplanner.optimization.models import EnergyFlow
from offgridplanner.optimization.models import Results
from offgridplanner.projects.exports import PdfReportBuilder
from offgridplanner.projects.exports import format_column_names
from offgridplanner.projects.exports import format_first_col
from offgridplanner.projects.models import Project
from offgridplanner.projects.views import populate_project_from_export
from offgridplanner.users.tests.factories import UserFactory

N_HOURS = 24  # keep the fabricated energy flow time series short/fast

# ---------- format_first_col ----------


class TestFormatFirstCol:
    def _apply(self, values):
        df = pd.DataFrame({"col": values})
        return format_first_col(df)["col"].tolist()

    def test_replaces_underscores_with_spaces(self):
        result = self._apply(["n_poles"])
        assert result == ["N poles"]

    def test_capitalizes_first_character(self):
        result = self._apply(["peak_demand"])
        assert result == ["Peak demand"]

    def test_replaces_lcoe_with_uppercase(self):
        result = self._apply(["lcoe_share_grid"])
        assert result == ["LCOE share grid"]

    def test_replaces_pv_with_uppercase(self):
        result = self._apply(["pv_capacity"])
        assert result == ["PV capacity"]

    def test_replaces_co2_with_uppercase(self):
        result = self._apply(["co2_emissions"])
        assert result == ["CO2 emissions"]

    def test_replaces_mg_with_minigrid(self):
        result = self._apply(["mg_connection_cost"])
        assert result == ["Mini-grid connection cost"]

    def test_res_replaced_with_full_label(self):
        result = self._apply(["res"])
        assert result == ["RES share"]

    def test_returns_dataframe(self):
        df = pd.DataFrame({"col": ["n_poles"]})
        result = format_first_col(df)
        assert isinstance(result, pd.DataFrame)

    def test_does_not_affect_other_columns(self):
        df = pd.DataFrame({"col": ["pv_capacity"], "other": [42]})
        result = format_first_col(df)
        assert result["other"].iloc[0] == 42  # noqa: PLR2004


# ---------- format_column_names ----------


class TestFormatColumnNames:
    def test_replaces_underscores_with_spaces_and_capitalizes(self):
        df = pd.DataFrame(columns=["n_poles", "cost_grid"])
        result = format_column_names(df)
        assert "N poles" in result.columns
        assert "Cost grid" in result.columns

    def test_capitalizes_first_character(self):
        df = pd.DataFrame(columns=["peak_demand"])
        result = format_column_names(df)
        assert "Peak demand" in result.columns

    def test_already_formatted_column_unchanged(self):
        df = pd.DataFrame(columns=["Value"])
        result = format_column_names(df)
        assert "Value" in result.columns

    def test_returns_same_dataframe(self):
        df = pd.DataFrame(columns=["a_b"])
        result = format_column_names(df)
        assert result is df

    def test_multiple_underscores(self):
        df = pd.DataFrame(columns=["very_long_column_name"])
        result = format_column_names(df)
        assert "Very long column name" in result.columns


# ---------- PdfReportBuilder ----------


def _zero_results_kwargs():
    """
    Results has ~80 scalar fields that a real simulation run always populates.
    Reflecting them keeps this fixture from going stale as fields are added.
    """
    skip = {"id", "simulation"}
    return {
        f.name: 0.0
        for f in Results._meta.get_fields()  # noqa: SLF001
        if hasattr(f, "attname") and f.name not in skip
    }


@pytest.fixture
def pdf_ready_project(db):
    """
    A fully populated project, built from the real example project fixture
    (nodes/links/energy system design/custom demand), plus a Results row and
    an EnergyFlow time series -- the two pieces populate_project_from_export
    doesn't create, since they're normally written by the optimization run.
    """
    with Path(EXAMPLE_PROJECT_PATH).open() as f:
        example_project_data = json.load(f)
    user = UserFactory()
    proj_id = populate_project_from_export(example_project_data, user)
    project = Project.objects.get(id=proj_id)

    results_kwargs = _zero_results_kwargs()
    results_kwargs.update(
        n_consumers=132,
        n_shs_consumers=0,
        n_poles=75,
        length_distribution_cable=5000,
        average_length_distribution_cable=50.0,
        length_connection_cable=2000,
        average_length_connection_cable=20.0,
        cost_grid=1000.0,
        lcoe=20.0,
        lcoh=15.0,
        lcoe_share_grid=10.0,
        lcoe_share_supply=90.0,
        res=80.0,
        surplus_rate=5.0,
        pv_capacity=100.0,
        battery_capacity=50.0,
        inverter_capacity=40.0,
        diesel_genset_capacity=10.0,
        fuel_cell_capacity=5.0,
        electrolyzer_capacity=5.0,
        h2_storage_capacity=20.0,
        peak_demand=30.0,
        base_load=5.0,
        average_annual_demand_per_consumer=500.0,
        total_annual_consumption=5000.0,
        upfront_invest_grid=1000.0,
        upfront_invest_diesel_genset=500.0,
        upfront_invest_inverter=400.0,
        upfront_invest_battery=600.0,
        upfront_invest_pv=1200.0,
        upfront_invest_h2_storage=300.0,
        upfront_invest_fuel_cell=250.0,
        upfront_invest_electrolyzer=250.0,
        upfront_invest_total=4500.0,
        co2_savings=10.0,
        co2_emissions=2.0,
        fuel_consumption=100.0,
        epc_total=900.0,
        epc_pv=300.0,
        epc_diesel_genset=100.0,
        epc_inverter=80.0,
        epc_battery=120.0,
        epc_h2_storage=60.0,
        epc_fuel_cell=50.0,
        epc_electrolyzer=50.0,
        cost_fuel=40.0,
    )
    Results.objects.get_or_create(
        simulation=project.simulation, defaults=results_kwargs
    )

    index = pd.date_range("2026-01-01", periods=N_HOURS, freq="h")
    energy_flow_df = pd.DataFrame(
        {
            "demand": [30.0] * N_HOURS,
            "dc_bus_to_battery": [1.0] * N_HOURS,
            "battery_to_dc_bus": [1.0] * N_HOURS,
            "dc_bus_to_electrolyzer": [1.0] * N_HOURS,
            "fuel_cell_to_dc_bus": [1.0] * N_HOURS,
            "dc_bus_to_surplus": [0.5] * N_HOURS,
            "hydrogen_bus_to_h2_storage": [0.2] * N_HOURS,
        },
        index=index,
    )
    energy_flow, _ = EnergyFlow.objects.get_or_create(project=project)
    energy_flow.input_df_to_data_field(energy_flow_df)
    energy_flow.save()

    return proj_id


@pytest.fixture
def dummy_img_dict():
    """A stand-in for the client-rendered chart images the real view builds."""
    keys = [
        "map",
        "sankeyDiagram",
        "energyFlows",
        "lcoeBreakdown",
        "demandTs",
        "demandCoverage",
    ]
    return {key: Spacer(1, 1) for key in keys}


@pytest.mark.django_db
class TestPdfReportBuilder:
    def _paragraph_texts(self, builder):
        return [el.text for el in builder.elements if isinstance(el, Paragraph)]

    def test_build_returns_doc_and_pdf_buffer(self, pdf_ready_project, dummy_img_dict):
        builder = PdfReportBuilder(pdf_ready_project, dummy_img_dict)
        doc, buffer = builder.build()
        pdf_bytes = buffer.getvalue()

        assert doc is not None
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000  # noqa: PLR2004

    def test_all_section_headings_present(self, pdf_ready_project, dummy_img_dict):
        builder = PdfReportBuilder(pdf_ready_project, dummy_img_dict)
        builder.build()
        texts = self._paragraph_texts(builder)

        for heading in [
            "1. Overview of Project Parameters",
            "2. Results",
            "2.1 Summary of Results",
            "2.2 Technical Results",
            "2.3 Economic Results",
            "2.4 Demand Results",
            "2.5 Environmental Results",
            "3. Tool Description",
            "3.1 Demand Estimation",
            "3.2 Grid Design Optimization",
            "3.3 Energy System Optimization",
        ]:
            assert any(heading in t for t in texts), f"Missing heading: {heading}"

    def test_project_name_rendered(self, pdf_ready_project, dummy_img_dict):
        builder = PdfReportBuilder(pdf_ready_project, dummy_img_dict)
        builder.build()
        texts = self._paragraph_texts(builder)

        assert any("Example project" in t for t in texts)

    def test_wraps_up_project_currency(self, pdf_ready_project, dummy_img_dict):
        builder = PdfReportBuilder(pdf_ready_project, dummy_img_dict)
        builder.build()

        assert builder.currency == "EUR"
