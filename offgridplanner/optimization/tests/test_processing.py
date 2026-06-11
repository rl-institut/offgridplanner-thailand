import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from config.settings.base import EXAMPLE_PROJECT_PATH
from offgridplanner.optimization.models import Nodes
from offgridplanner.optimization.processing import OptimizationDataHandler
from offgridplanner.optimization.supply.demand_estimation import LOAD_PROFILES
from offgridplanner.projects.views import populate_project_from_export
from offgridplanner.steps.models import CustomDemand
from offgridplanner.users.tests.factories import UserFactory

FLOAT_TOLERANCE = 1e-9

N_HOURS = 24  # use one day to keep tests fast


def _nodes_from(rows):
    n = Nodes()
    n.data = json.dumps(rows)
    return n


def _make_handler(  # noqa: PLR0913
    *,
    do_demand_estimation=False,
    uploaded_series=None,
    annual_growth=None,
    project_lifetime=20,
    nodes=None,
    custom_demand=None,
    n_days=1,
):
    """Minimal OptimizationDataHandler bypassing DB-heavy __init__."""
    handler = OptimizationDataHandler.__new__(OptimizationDataHandler)
    handler.project_lifetime = project_lifetime

    options = MagicMock()
    options.do_demand_estimation = do_demand_estimation
    handler.options = options

    if custom_demand is None:
        custom_demand = MagicMock()
        custom_demand.annual_demand_increase = annual_growth

    project = MagicMock()
    project.customdemand = custom_demand
    project.n_days = n_days
    if nodes is not None:
        project.nodes = nodes
    handler.project = project

    if uploaded_series is not None:
        df = pd.DataFrame({"demand": uploaded_series.to_numpy()})
        project.customdemand.uploaded_data = df.to_json()
        project.customdemand.annual_demand_increase = annual_growth

    return handler


# ---------- Integration smoke test ----------


@pytest.fixture
def example_project_data():
    with Path(EXAMPLE_PROJECT_PATH).open() as f:
        return json.load(f)


@pytest.mark.django_db
def test_collect_project_demand_integration(example_project_data):
    user = UserFactory()
    proj_id = populate_project_from_export(example_project_data, user)
    handler = OptimizationDataHandler(proj_id)
    demand = handler.collect_project_demand()
    assert isinstance(demand, pd.Series)
    assert len(demand) > 0
    assert (demand >= 0).all()


# ---------- Demand estimation branch ----------


class TestDemandEstimationBranch:
    @pytest.fixture
    def household_nodes(self):
        return _nodes_from(
            [
                {
                    "label": "h1",
                    "consumer_type": "household",
                    "consumer_detail": "default",
                    "is_connected": True,
                    "custom_specification": "",
                }
            ]
        )

    @pytest.fixture
    def enterprise_nodes(self):
        return _nodes_from(
            [
                {
                    "label": "e1",
                    "consumer_type": "enterprise",
                    "consumer_detail": "Household plus shop",
                    "is_connected": True,
                    "custom_specification": "",
                }
            ]
        )

    @pytest.fixture
    def mixed_nodes(self):
        return _nodes_from(
            [
                {
                    "label": "h1",
                    "consumer_type": "household",
                    "consumer_detail": "default",
                    "is_connected": True,
                    "custom_specification": "",
                },
                {
                    "label": "e1",
                    "consumer_type": "enterprise",
                    "consumer_detail": "Household plus shop",
                    "is_connected": True,
                    "custom_specification": "",
                },
            ]
        )

    def test_exact_household_low_tier_demand(self, household_nodes):
        cd = CustomDemand(low=1.0, middle=0.0, high=0.0)
        handler = _make_handler(
            do_demand_estimation=True,
            nodes=household_nodes,
            custom_demand=cd,
            n_days=1,
        )
        result = handler.collect_project_demand().reset_index(drop=True)

        expected = (
            LOAD_PROFILES["Household_Low Consumption"]
            .iloc[:N_HOURS]
            .reset_index(drop=True)
        )
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_exact_enterprise_demand(self, enterprise_nodes):
        cd = CustomDemand(low=0.0, middle=0.0, high=0.0)
        handler = _make_handler(
            do_demand_estimation=True,
            nodes=enterprise_nodes,
            custom_demand=cd,
            n_days=1,
        )
        result = handler.collect_project_demand().reset_index(drop=True)

        expected = (
            LOAD_PROFILES["Enterprise_Household plus shop"]
            .iloc[:N_HOURS]
            .reset_index(drop=True)
        )
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_exact_mixed_nodes_demand(self, mixed_nodes):
        cd = CustomDemand(low=1.0, middle=0.0, high=0.0)
        handler = _make_handler(
            do_demand_estimation=True,
            nodes=mixed_nodes,
            custom_demand=cd,
            n_days=1,
        )
        result = handler.collect_project_demand().reset_index(drop=True)

        expected = (
            LOAD_PROFILES["Household_Low Consumption"].iloc[:N_HOURS]
            + LOAD_PROFILES["Enterprise_Household plus shop"].iloc[:N_HOURS]
        ).reset_index(drop=True)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_ignores_uploaded_data_when_do_demand_estimation_true(
        self, household_nodes
    ):
        cd = CustomDemand(low=1.0, middle=0.0, high=0.0)
        # Provide uploaded data with a conspicuously different value (9999)
        uploaded = pd.Series([9999.0] * N_HOURS)
        handler = _make_handler(
            do_demand_estimation=True,
            uploaded_series=uploaded,
            nodes=household_nodes,
            custom_demand=cd,
            n_days=1,
        )
        result = handler.collect_project_demand()
        assert result.max() < 9999.0  # noqa: PLR2004

    def test_result_length_matches_n_days(self, household_nodes):
        cd = CustomDemand(low=1.0, middle=0.0, high=0.0)
        handler = _make_handler(
            do_demand_estimation=True,
            nodes=household_nodes,
            custom_demand=cd,
            n_days=2,
        )
        assert len(handler.collect_project_demand()) == 2 * 24


# ---------- Uploaded data branch ----------


class TestUploadedDataBranch:
    @pytest.fixture
    def uploaded_demand(self):
        # Non-whole floats avoid int64/float64 dtype mismatch after JSON roundtrip
        return pd.Series([1.5 + i * 0.1 for i in range(N_HOURS)])

    def test_returns_series(self, uploaded_demand):
        handler = _make_handler(uploaded_series=uploaded_demand)
        assert isinstance(handler.collect_project_demand(), pd.Series)

    def test_exact_values_match_uploaded_data(self, uploaded_demand):
        handler = _make_handler(uploaded_series=uploaded_demand, annual_growth=None)
        result = handler.collect_project_demand().reset_index(drop=True)
        pd.testing.assert_series_equal(result, uploaded_demand, check_names=False)

    def test_length_matches_uploaded_data(self, uploaded_demand):
        handler = _make_handler(uploaded_series=uploaded_demand)
        assert len(handler.collect_project_demand()) == len(uploaded_demand)


# ---------- Annual demand increase ----------


class TestAnnualDemandIncrease:
    @pytest.fixture
    def base_demand(self):
        return pd.Series([1.5] * N_HOURS)

    def test_none_growth_returns_original_demand(self, base_demand):
        handler = _make_handler(uploaded_series=base_demand, annual_growth=None)
        result = handler.collect_project_demand().reset_index(drop=True)
        pd.testing.assert_series_equal(result, base_demand, check_names=False)

    def test_positive_growth_increases_demand(self, base_demand):
        handler = _make_handler(
            uploaded_series=base_demand,
            annual_growth=0.05,
            project_lifetime=10,
        )
        assert handler.collect_project_demand().sum() > base_demand.sum()

    def test_mean_growth_factor_math(self, base_demand):
        growth = 0.1
        years = 3
        handler = _make_handler(
            uploaded_series=base_demand,
            annual_growth=growth,
            project_lifetime=years,
        )
        result = handler.collect_project_demand().reset_index(drop=True)

        yearly_factors = [(1 + growth) ** y for y in range(years)]
        expected_factor = sum(yearly_factors) / years
        expected = (base_demand * expected_factor).reset_index(drop=True)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_one_year_project_applies_no_scaling(self, base_demand):
        # range(1) = [0] → (1+g)^0 = 1.0 → mean factor = 1.0
        handler = _make_handler(
            uploaded_series=base_demand,
            annual_growth=0.2,
            project_lifetime=1,
        )
        result = handler.collect_project_demand().reset_index(drop=True)
        pd.testing.assert_series_equal(result, base_demand, check_names=False)

    def test_result_scales_linearly_with_base_demand(self):
        base = pd.Series([2.5] * N_HOURS)
        double = base * 2
        growth, years = 0.08, 15

        result_base = (
            _make_handler(
                uploaded_series=base, annual_growth=growth, project_lifetime=years
            )
            .collect_project_demand()
            .reset_index(drop=True)
        )

        result_double = (
            _make_handler(
                uploaded_series=double, annual_growth=growth, project_lifetime=years
            )
            .collect_project_demand()
            .reset_index(drop=True)
        )

        pd.testing.assert_series_equal(
            result_double, result_base * 2, check_names=False
        )

    def test_higher_growth_rate_produces_larger_demand(self, base_demand):
        low = _make_handler(
            uploaded_series=base_demand, annual_growth=0.01, project_lifetime=20
        ).collect_project_demand()
        high = _make_handler(
            uploaded_series=base_demand, annual_growth=0.10, project_lifetime=20
        ).collect_project_demand()
        assert high.sum() > low.sum()
