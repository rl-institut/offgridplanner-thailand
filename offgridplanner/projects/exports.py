import io
from types import SimpleNamespace

import pandas as pd
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import get_object_or_404
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import KeepTogether
from reportlab.platypus import ListFlowable
from reportlab.platypus import ListItem
from reportlab.platypus import PageBreak
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Spacer
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from svglib.svglib import svg2rlg

from offgridplanner.optimization.processing import PreProcessor
from offgridplanner.projects.helpers import collect_project_dataframes
from offgridplanner.projects.helpers import compute_derived_hydrogen_kpis
from offgridplanner.projects.models import Project


def format_first_col(df):
    df.iloc[:, 0] = (
        df.iloc[:, 0]
        .astype(str)
        .str.replace("shs", "SHS")
        .str.replace("_", " ")
        .str.capitalize()
        .str.replace("Mg", "Mini-grid")
        .str.replace("Lcoe", "LCOE")
        .str.replace("Pv", "PV")
        .str.replace(" dc ", " DC ")
        .str.replace("Co2", "CO2")
        .str.replace("Res", "RES share")
    )
    return df


def format_column_names(df):
    df.columns = [col.replace("_", " ").capitalize() for col in df.columns]
    return df


def prepare_data_for_export(  # noqa:PLR0913,PLR0915
    input_df,
    energy_system_design,
    energy_flow_df,
    results_df,
    nodes_df,
    links_df,
    currency,
):
    # TODO set units etc. with mapping instead
    """
    Prepares dataframes for export by formatting columns, adding units, and renaming fields.
    """

    # Merge input data and rename columns
    input_df["start_date"] = input_df["start_date"].dt.strftime("%m/%d/%Y, %H:%M:%S")
    input_df = pd.concat([input_df.T, energy_system_design.T])
    input_df.columns = ["User specified input parameters"]
    input_df.index.name = ""
    input_df = input_df.rename(
        index={"shs_max_grid_cost": "shs_max_specific_marginal_grid_cost"}
    )
    input_df["Unit"] = ""
    input_df.index.str.replace("_parameters_", "_parameter: ")
    input_df.index.str.replace("_settings_", "_settings: ")
    input_df.loc["n_days", "Unit"] = "days"
    input_df.loc["interest_rate", "Unit"] = "%"
    input_df.loc[["distribution_cable_capex", "connection_cable_capex"], "Unit"] = (
        f"{currency}/m"
    )
    input_df.loc["pole_capex"] = f"{currency}/pole"
    input_df.loc[input_df.index.str.contains("lifetime"), "Unit"] = "years"
    input_df.loc[input_df.index.str.contains("length"), "Unit"] = "m"
    input_df.loc[input_df.index.str.contains("_capex"), "Unit"] = f"{currency}/kWh"
    input_df.loc[input_df.index.str.contains("_opex"), "Unit"] = f"{currency}/(kW a)"
    input_df.loc[input_df.index.str.contains("_fuel"), "Unit"] = f"{currency}/l"
    input_df.loc[input_df.index.str.contains("_fuel_cost"), "Unit"] = f"{currency}/l"
    input_df.loc[input_df.index.str.contains("_fuel_lhv"), "Unit"] = "kWh/kg"
    input_df.loc[input_df.index.str.contains("_capacity"), "Unit"] = "kWh"
    input_df.loc[["battery_parameters_capex"], "Unit"] = f"{currency}/kWh"
    input_df.loc[["mg_connection_cost"], "Unit"] = f"{currency}"
    input_df.loc[["shs_max_specific_marginal_grid_cost"], "Unit"] = "ct/kWh"
    input_df = input_df.reset_index()
    input_df = format_first_col(input_df)
    cols = [
        col.replace("_", " ").capitalize() + " [kW]"
        if "content" not in col
        else col.replace("_", " ").capitalize() + " [kWh]"
        for col in energy_flow_df.columns
    ]
    energy_flow_df.columns = cols
    energy_flow_df = energy_flow_df.reset_index()
    results_df = results_df.T.reset_index()
    results_df["Unit"] = ""
    results_df.columns = ["", "Value", "Unit"]
    results_df = format_first_col(results_df)
    results_df = results_df.set_index("")
    results_df.loc[results_df.index.str.contains("length"), "Unit"] = "m"
    results_df.loc[results_df.index.str.contains("CO2"), "Unit"] = "t/a"
    results_df.loc[results_df.index.str.contains("Upfront"), "Unit"] = f"{currency}"
    results_df.loc[results_df.index.str.contains("Cost"), "Unit"] = f"{currency}/a"
    results_df.loc[results_df.index.str.contains("Epc"), "Unit"] = f"{currency}/a"
    results_df.loc[results_df.index.str.contains("capacity"), "Unit"] = f"{currency}/kW"
    results_df.loc[["Battery capacity"], "Unit"] = f"{currency}/kWh"
    results_df.loc[
        [
            "Max voltage drop",
            "RES share",
            "Surplus rate",
            "Shortage total",
            "Max shortage",
        ],
        "Unit",
    ] = "%"
    results_df.loc[
        [
            "Average annual demand per consumer",
            "Fuel consumption",
            "Total annual consumption",
            "Surplus",
        ],
        "Unit",
    ] = "kWh/a"
    results_df = results_df[~results_df.index.str.contains("Time")]
    results_df = results_df[~results_df.index.str.contains(" to ")]
    results_df.loc[["LCOE"], "Unit"] = "c/kWh"
    results_df.loc[["Base load", "Peak demand"], "Unit"] = "kW"
    results_df = results_df.T
    results_df = results_df.T.reset_index()
    for col in ["distribution_cost", "parent"]:
        if col in nodes_df.columns:
            nodes_df = nodes_df.drop(columns=[col])
    nodes_df = format_column_names(nodes_df)
    links_df = (
        links_df[["link_type", "length", "lat_from", "lon_from", "lat_to", "lon_to"]]
        if not links_df.empty
        else links_df
    )
    links_df = format_column_names(links_df)
    return input_df, energy_flow_df, results_df, nodes_df, links_df


class PdfReportBuilder:
    """Builds the off-grid planning PDF report from a project's data and pre-rendered chart images."""

    @staticmethod
    def _figure_caption(text):
        return Paragraph(
            text,
            ParagraphStyle(
                "FigureCaption",
                fontSize=8,
                alignment=TA_CENTER,
                spaceAfter=24,
                fontName="Helvetica-Oblique",
            ),
        )

    def __init__(self, proj_id, img_dict):
        self.proj_id = proj_id
        self.project = get_object_or_404(Project, id=proj_id)
        self.currency = self.project.currency
        self.img_dict = img_dict

        dataframes = collect_project_dataframes(proj_id)
        self.energy_flow_df = dataframes["energy_flow_df"]
        self.input_df = dataframes["input_parameters_df"]
        self.results_df = dataframes["results_df"]
        self.energy_system_design = dataframes["energy_system_design_df"]
        self.nodes_df = dataframes["nodes_df"]
        self.links_df = dataframes["links_df"]
        self.custom_demand_df = dataframes["custom_demand_df"]
        self.elements = []

    def build(self):
        """
        Public orchestrator. Returns a tuple (doc, buffer): the ReportLab
        document object and a BytesIO buffer containing the rendered PDF.
        """
        self._compute_raw_kpis()
        self._prepare_dataframes()
        self._build_namespaces()
        self._load_styles()
        self._build_title_and_toc()
        self._build_section_1_overview()
        self._build_section_2_results()
        self._build_section_3_tool_description()
        return self._render()

    # ---- data preparation -------------------------------------------------

    def _compute_raw_kpis(self):
        """
        These KPIs aren't persisted on the Results model, so they have to be
        derived from the raw energy flow time series before _prepare_dataframes
        renames its columns. compute_derived_energy_kpis is shared with
        offgridplanner/steps/views.py:simulation_results.
        """
        energy_flow_df = self.energy_flow_df
        if "demand" not in energy_flow_df.columns:
            energy_flow_df["demand"] = PreProcessor(self.proj_id).demand.to_numpy()
        self.demand_ts = energy_flow_df["demand"].copy()

        lhv = self.energy_system_design["fuel_cell_parameters_fuel_lhv"].iloc[0]
        derived_kpis = compute_derived_hydrogen_kpis(energy_flow_df, lhv)
        self.h2_production_kg = derived_kpis["h2_production_kg"]
        self.operation_hours_battery = derived_kpis["operation_hours_battery"]
        self.operation_hours_electrolyzer = derived_kpis["operation_hours_electrolyzer"]
        self.operation_hours_fuel_cell = derived_kpis["operation_hours_fuel_cell"]
        self.surplus_total_kwh = derived_kpis["surplus_total_kwh"]

    def _prepare_dataframes(self):
        (
            self.input_df,
            self.energy_flow_df,
            self.results_df,
            self.nodes_df,
            self.links_df,
        ) = prepare_data_for_export(
            self.input_df,
            self.energy_system_design,
            self.energy_flow_df,
            self.results_df,
            self.nodes_df,
            self.links_df,
            self.currency,
        )

    def _build_namespaces(self):
        """Convert DataFrames to SimpleNamespace for easier attribute access."""
        self.input_data = SimpleNamespace(
            **dict(
                zip(
                    self.input_df.iloc[:, 0].str.replace(" ", "_").str.lower(),
                    self.input_df.iloc[:, 1],
                    strict=False,
                )
            )
        )
        self.results = SimpleNamespace(
            **dict(
                zip(
                    self.results_df.iloc[:, 0].str.replace(" ", "_").str.lower(),
                    self.results_df.iloc[:, 1],
                    strict=False,
                )
            )
        )

    # ---- styles + page callbacks -------------------------------------------

    def _load_styles(self):
        self.styles = getSampleStyleSheet()
        self.subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=self.styles["Title"],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=24,
            leading=28,
        )
        self.body_style = ParagraphStyle(
            "BodyText",
            parent=self.styles["BodyText"],
            fontSize=12,
            alignment=TA_JUSTIFY,
            leading=26,
            spaceAfter=12,
        )
        self.toc_title_style = ParagraphStyle(
            "toc_title",
            parent=self.styles["Title"],
            fontSize=16,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
        self.table_style = TableStyle(
            [
                # Top line above header
                ("LINEABOVE", (0, 0), (-1, 0), 1, "BLACK"),
                # Bottom line below header (midrule)
                ("LINEBELOW", (0, 0), (-1, 0), 1, "BLACK"),
                # Bottom line below the last row
                ("LINEBELOW", (0, -1), (-1, -1), 1, "BLACK"),
                # Alignment:
                ("ALIGN", (0, 0), (0, -1), "LEFT"),  # First column left-aligned
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),  # Second column right-aligned
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),  # Third column right-aligned
                # Padding
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
        self.header_style = ParagraphStyle(
            "Header",
            parent=self.styles["Heading4"],
            fontSize=12,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            leading=14,
        )

    def _draw_header(self, canvas, doc):
        """
        Draws the Offgridplanner logo top-left and the Green-H2Islands logo
        top-right, positioned in the page's top margin band.
        """
        canvas.saveState()
        page_width, page_height = A4
        logo_height = 0.4 * inch
        logo_y = page_height - 0.7 * inch

        left_logo_path = staticfiles_storage.path("assets/logos/LogoOffgridplanner.svg")
        left_drawing = svg2rlg(left_logo_path)
        scale = logo_height / left_drawing.height
        left_drawing.width *= scale
        left_drawing.height *= scale
        left_drawing.scale(scale, scale)
        renderPDF.draw(left_drawing, canvas, doc.leftMargin, logo_y)

        right_logo_path = staticfiles_storage.path(
            "assets/logos/Green-H2Islands-Full-Logo.png"
        )
        right_reader = ImageReader(right_logo_path)
        right_img_width, right_img_height = right_reader.getSize()
        right_width = logo_height * right_img_width / right_img_height
        canvas.drawImage(
            right_reader,
            page_width - doc.rightMargin - right_width,
            logo_y,
            width=right_width,
            height=logo_height,
            mask="auto",
        )
        canvas.restoreState()

    def _add_page_number(self, canvas, doc):
        """
        Adds the page number at the bottom right of the page.
        Page numbering starts at 1 from the second page.
        """
        self._draw_header(canvas, doc)
        page_num = doc.page
        if page_num > 1:
            display_num = page_num - 1
            text = f"Page {display_num}"
            canvas.setFont("Helvetica", 9)
            x_position = 185 * mm
            y_position = 15 * mm
            canvas.drawRightString(x_position, y_position, text)

    def _on_first_page(self, canvas, doc):
        """Draws the header logos on the title page."""
        self._draw_header(canvas, doc)

    # ---- content sections ---------------------------------------------------

    def _build_title_and_toc(self):
        # Add titles (logos are drawn in the page header, see _draw_header)
        title = Paragraph("Off-Grid System Planning Results", self.styles["Title"])
        subtitle = Paragraph(
            "Energy System Optimization Carried Out with the Tool Offgridplanner (https://offgridplanner.org)",
            self.subtitle_style,
        )

        self.elements.append(
            KeepTogether(
                [
                    title,
                    subtitle,
                    Spacer(1, 12),
                ]
            )
        )

        # Add project details
        self.elements.append(
            Paragraph(f"Project Name: {self.input_data.name}", self.body_style)
        )
        self.elements.append(
            Paragraph(
                f"Project Description: {self.input_data.description}", self.body_style
            )
        )

        # Add Table of Contents
        self.elements.append(Spacer(1, 48))
        self.elements.append(Paragraph("Table of Contents", self.toc_title_style))
        self.elements.append(Spacer(1, 12))

        indent = "&nbsp;&nbsp;&nbsp;&nbsp;"
        toc = [
            ["Section", "Page"],
            ["1. Overview of Project Parameters", "&nbsp;&nbsp;1"],
            ["2. Results", "&nbsp;&nbsp;2"],
            [f"{indent}2.1 Summary of Results", "&nbsp;&nbsp;2"],
            [f"{indent}2.2 Technical Results", "&nbsp;&nbsp;2"],
            [f"{indent}2.3 Economic Results", "&nbsp;&nbsp;6"],
            [f"{indent}2.4 Demand Results", "&nbsp;&nbsp;8"],
            [f"{indent}2.5 Environmental Results", "&nbsp;&nbsp;10"],
            ["3. Tool Description", "&nbsp;&nbsp;11"],
            [f"{indent}3.1 Demand Estimation", "&nbsp;&nbsp;11"],
            [f"{indent}3.2 Grid Design Optimization", "&nbsp;&nbsp;11"],
            [f"{indent}3.3 Energy System Optimization", "&nbsp;&nbsp;11"],
        ]

        self.planning_steps = []
        if self.input_data.do_demand_estimation:
            self.planning_steps.append("Demand estimation based on selected consumers")
        if self.input_data.do_grid_optimization:
            grid_text = "Spatial optimization of distribution grid"
            grid_text += f" with the option to exclude consumers with specific marginal connection costs above {self.input_data.shs_max_specific_marginal_grid_cost} ct/kWh"
            self.planning_steps.append(grid_text)
        if self.input_data.do_es_design_optimization:
            self.planning_steps.append(
                "Design optimization of energy converters and storage"
            )

        # Create ToC entries
        toc_entries = []
        self.left_margin = self.right_margin = 72  # 1 inch margins
        self.max_table_width = A4[0] - self.left_margin - self.right_margin
        page_number_width = 50  # Width reserved for page numbers

        for section, page in toc:
            section_para = Paragraph(f"<b>{section}</b>", self.header_style)
            page_para = Paragraph(f"<b>{page}</b>", self.header_style)
            toc_entries.append([section_para, page_para])

        # Define column widths
        col_widths = [
            self.max_table_width - page_number_width,  # section titles
            page_number_width,  # page numbers
        ]

        # Create ToC Table
        toc_table = Table(toc_entries, colWidths=col_widths)
        toc_table.setStyle(self.table_style)
        self.elements.append(toc_table)

        self.elements.append(PageBreak())

    def _build_section_1_overview(self):
        self.elements.append(
            Paragraph("1. Overview of Project Parameters", self.styles["Heading1"])
        )
        self.elements.append(Spacer(1, 24))

        if not self.nodes_df.empty:
            latitude = self.nodes_df["Latitude"].median().round(4)
            longitude = self.nodes_df["Longitude"].median().round(4)

            overview_text = (
                f"For the location at latitude {latitude}° and longitude {longitude}° with {self.results.n_consumers} selected consumers, "
                "the following planning steps were carried out:"
            )
        else:
            overview_text = "The following planning steps were carried out:"
        self.elements.append(Paragraph(overview_text, self.body_style))

        # Create Planning Steps List
        planning_steps_flowable = ListFlowable(
            [
                ListItem(Paragraph(step, self.body_style), leftIndent=20)
                for step in self.planning_steps
            ],
            bulletType="bullet",
            spaceBefore=12,
            spaceAfter=12,
            bulletFontName="Helvetica",
            bulletFontSize=12,
            bulletColor="black",
        )
        self.elements.append(planning_steps_flowable)

        # Economic Assessment Text
        economic_assessment_text = (
            f"For the economic assessment, a project duration of {self.input_data.lifetime} years and an interest rate of "
            f"{self.input_data.interest_rate}% have been applied."
        )
        if self.input_data.do_es_design_optimization:
            economic_assessment_text += (
                " The design optimization of the energy converters and storage is based on a unit commitment carried out for a period "
                f"of {self.input_data.n_days} days. The operating costs resulting from this period are scaled up to the project's lifetime, "
                "taking into account the time value of money according to the specified interest rate."
            )
        self.elements.append(Paragraph(economic_assessment_text, self.body_style))

        self.elements.append(PageBreak())

    def _build_section_2_results(self):
        self.elements.append(Paragraph("2. Results", self.styles["Heading1"]))
        self.elements.append(Spacer(1, 24))

        self._upfront_invest_total = self.results_df[
            self.results_df.iloc[:, 0].str.contains("Upfront")
        ]["Value"].sum()

        self._build_section_2_1_summary()
        self._build_section_2_2_technical()
        self._build_section_2_3_economic()
        self._build_section_2_4_demand()
        self._build_section_2_5_environmental()

    def _build_section_2_1_summary(self):
        results = self.results
        input_data = self.input_data

        self.elements.append(
            Paragraph("2.1 Summary of Results", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 12))

        summary_data = [["KPI", "Value"]]
        summary_data.append(["LCOE", f"{results.lcoe:,.1f} cents/kWh"])
        if input_data.do_es_design_optimization and results.h2_storage_capacity > 0:
            summary_data.append(["LCOH", f"{results.lcoh:,.1f} cents/kWh"])
        summary_data.append(
            [
                "Total Upfront Investment",
                f"{self._upfront_invest_total:,.0f} {self.currency}",
            ]
        )
        if input_data.do_es_design_optimization:
            summary_data.append(["Renewable Energy Share", f"{results.res_share:.1f}%"])
        summary_table = Table(summary_data, colWidths=[250, 150])
        summary_table.setStyle(self.table_style)
        self.elements.append(summary_table)
        self.elements.append(Spacer(1, 24))

    def _build_section_2_2_technical(self):
        self.elements.append(
            Paragraph("2.2 Technical Results", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 12))

        self._build_technical_capacity()
        self._build_technical_grid()
        self._build_technical_energy_flows()

        self.elements.append(PageBreak())

    def _capacity_dict(self):
        results = self.results
        capacity_dict = {}
        if results.pv_capacity > 0:
            capacity_dict["PV"] = f"{results.pv_capacity:,.1f} kW"
        if results.diesel_genset_capacity > 0:
            capacity_dict["Diesel Generator"] = (
                f"{results.diesel_genset_capacity:,.1f} kW"
            )
        if results.inverter_capacity > 0:
            capacity_dict["Inverter"] = f"{results.inverter_capacity:,.1f} kW"
        if results.rectifier_capacity > 0:
            capacity_dict["Rectifier"] = f"{results.rectifier_capacity:,.1f} kW"
        if results.battery_capacity:
            capacity_dict["Battery System"] = (
                f"{results.battery_capacity:,.1f} kWh"  # Corrected typo
            )
        if results.electrolyzer_capacity > 0:
            capacity_dict["Electrolyzer"] = f"{results.electrolyzer_capacity:,.1f} kW"
        if results.fuel_cell_capacity > 0:
            capacity_dict["Fuel Cell"] = f"{results.fuel_cell_capacity:,.1f} kW"
        if results.h2_storage_capacity > 0:
            capacity_dict["H2 Storage"] = f"{results.h2_storage_capacity:,.1f} kWh"
        if self.h2_production_kg > 0:
            capacity_dict["Hydrogen Production"] = f"{self.h2_production_kg:,.1f} kg/a"
        return capacity_dict

    def _operation_hours_dict(self):
        operation_hours_dict = {}
        if self.operation_hours_battery > 0:
            operation_hours_dict["Battery"] = f"{self.operation_hours_battery:,.0f} h"
        if self.operation_hours_electrolyzer > 0:
            operation_hours_dict["Electrolyzer"] = (
                f"{self.operation_hours_electrolyzer:,.0f} h"
            )
        if self.operation_hours_fuel_cell > 0:
            operation_hours_dict["Fuel Cell"] = (
                f"{self.operation_hours_fuel_cell:,.0f} h"
            )
        return operation_hours_dict

    def _build_technical_capacity(self):
        results = self.results

        if not self.input_data.do_es_design_optimization:
            return

        energy_design_intro = "The minimization of the project's total costs during project lifetime results in the following installations:"
        self.elements.append(Paragraph(energy_design_intro, self.body_style))

        table_data = [["Unit", "Capacity"], *self._capacity_dict().items()]
        capacity_table = Table(table_data, colWidths=[250, 150])
        capacity_table.setStyle(self.table_style)
        self.elements.append(capacity_table)
        self.elements.append(Spacer(1, 12))

        operation_hours_dict = self._operation_hours_dict()
        if operation_hours_dict:
            op_hours_data = [
                ["Component", "Operation Hours"],
                *operation_hours_dict.items(),
            ]
            op_hours_table = Table(op_hours_data, colWidths=[250, 150])
            op_hours_table.setStyle(self.table_style)
            self.elements.append(op_hours_table)
            self.elements.append(Spacer(1, 24))

        system_performance_text = (
            f"With this system, a renewable energy share of {results.res_share:.1f}% is achieved. "
            f"An electricity surplus of {results.surplus_rate:.1f}% occurs. "
        )
        self.elements.append(Paragraph(system_performance_text, self.body_style))

    def _build_technical_grid(self):
        results = self.results
        input_data = self.input_data

        if not input_data.do_grid_optimization:
            return

        self.elements.append(self.img_dict.get("map"))
        self.elements.append(
            self._figure_caption("Figure: Distribution Grid of the Off-Grid System")
        )

        connected_text = f"Out of the total {results.n_consumers} selected consumers, "
        if results.n_shs_consumers == 0:
            connected_text += "all were connected to the grid."
        else:
            num_unconnected = results.n_shs_consumers
            consumer_word = "consumer" if num_unconnected == 1 else "consumers"
            threshold = input_data.shs_max_specific_marginal_grid_cost
            connected_text += (
                f"{num_unconnected} {consumer_word} were not connected to the grid because their specific marginal connection costs exceeded "
                f"the user-defined threshold of {threshold} ct/kWh. Therefore, these consumers will need to be equipped with a solar home system "
                "instead."
            )
        self.elements.append(Paragraph(connected_text, self.body_style))

        grid_requirements_text = (
            f"The grid requires {results.n_poles:,.0f} poles, {results.length_distribution_cable:,.0f} meters of distribution cable "
            f"(avg. {results.average_length_distribution_cable:,.1f} m per connection), and "
            f"{results.length_connection_cable:,.0f} meters of connection cable (avg. {results.average_length_connection_cable:,.1f} m per connection). "
            f"The upfront grid investment costs amount to {results.upfront_invest_grid:,.0f} {self.currency}. "
            "The positioning of the poles and the layout of the connection cables are shown on the attached map."
        )
        self.elements.append(Paragraph(grid_requirements_text, self.body_style))
        self.elements.append(Spacer(1, 12))

    def _build_technical_energy_flows(self):
        if not self.input_data.do_es_design_optimization:
            return

        sankey_text = "The presented accumulated Sankey diagram visualizes the extent to which each component contributes to meeting the demand."
        self.elements.append(Paragraph(sankey_text, self.body_style))
        self.elements.append(self.img_dict.get("sankeyDiagram"))
        self.elements.append(
            self._figure_caption(
                "Figure: Sankey Diagram Representing the Energy Flow in the System"
            )
        )

        additional_diagrams_text = (
            "The following diagram illustrates an exemplary period at the beginning of the "
            "simulation timeframe, depicting the system's energy flows."
        )
        self.elements.append(Paragraph(additional_diagrams_text, self.body_style))
        self.elements.append(self.img_dict.get("energyFlows"))
        self.elements.append(
            self._figure_caption("Figure: Energy Flows with 1-Hour Resolution")
        )

    def _build_section_2_3_economic(self):
        results = self.results
        input_data = self.input_data

        if not input_data.do_es_design_optimization:
            return

        self.elements.append(Paragraph("2.3 Economic Results", self.styles["Heading2"]))
        self.elements.append(Spacer(1, 12))

        upfront_invest_converters_and_storage = (
            self._upfront_invest_total - results.upfront_invest_grid
        )

        economic_costs_text = (
            f"The total upfront investment costs amount to {self._upfront_invest_total:,.0f} {self.currency}. "
            f"Of this, {results.upfront_invest_grid:,.0f} {self.currency} is allocated to grid investment costs, and "
            f"{upfront_invest_converters_and_storage:,.0f} {self.currency} is allocated to energy converters and storage systems."
        )
        self.elements.append(Paragraph(economic_costs_text, self.body_style))

        lcoe_text = f"The Levelized Cost of Electricity for the energy system is {results.lcoe:,.0f} cents per kWh."
        self.elements.append(Paragraph(lcoe_text, self.body_style))

        self.elements.append(self.img_dict.get("lcoeBreakdown"))
        self.elements.append(
            self._figure_caption("Figure: Levelized Cost of Electricity Breakdown")
        )

        economic_details_text = (
            "The following table lists the respective upfront investment costs of individual "
            "components of the energy system, as well as the annualized costs."
        )
        self.elements.append(Paragraph(economic_details_text, self.body_style))

        table_data = [
            [
                "Component of Energy System",
                "Upfront Investment Costs",
                "Annualized Costs",
            ],
        ]
        if input_data.do_grid_optimization:
            table_data.append(
                [
                    "Grid",
                    f"{results.upfront_invest_grid:,.0f} {self.currency}",
                    f"{results.cost_grid:,.0f} {self.currency}",
                ]
            )
        table_data += [
            [
                "PV",
                f"{results.upfront_invest_pv:,.0f} {self.currency}",
                f"{results.epc_pv:,.0f} {self.currency}",
            ],
            [
                "Diesel Genset",
                f"{results.upfront_invest_diesel_genset:,.0f} {self.currency}",
                f"{results.epc_diesel_genset:,.0f} {self.currency}",
            ],
            [
                "Inverter",
                f"{results.upfront_invest_inverter:,.0f} {self.currency}",
                f"{results.epc_inverter:,.0f} {self.currency}",
            ],
            [
                "Rectifier",
                f"{results.upfront_invest_rectifier:,.0f} {self.currency}",
                f"{results.epc_rectifier:,.0f} {self.currency}",
            ],
            [
                "Battery",
                f"{results.upfront_invest_battery:,.0f} {self.currency}",
                f"{results.epc_battery:,.0f} {self.currency}",
            ],
            [
                "H2 Storage",
                f"{results.upfront_invest_h2_storage:,.0f} {self.currency}",
                f"{results.epc_h2_storage:,.0f} {self.currency}",
            ],
            [
                "Electrolyzer",
                f"{results.upfront_invest_electrolyzer:,.0f} {self.currency}",
                f"{results.epc_electrolyzer:,.0f} {self.currency}",
            ],
            [
                "Fuel Cell",
                f"{results.upfront_invest_fuel_cell:,.0f} {self.currency}",
                f"{results.epc_fuel_cell:,.0f} {self.currency}",
            ],
            ["Diesel Fuel", "-", f"{results.cost_fuel:,.0f} {self.currency}"],
        ]
        table_data.append(
            [
                "Total",
                f"{self._upfront_invest_total:,.0f} {self.currency}",
                f"{results.epc_total:,.0f} {self.currency}",
            ]
        )

        economic_table = Table(table_data, colWidths=[200, 100, 100])
        economic_table.setStyle(self.table_style)
        self.elements.append(economic_table)
        self.elements.append(Spacer(1, 24))
        self.elements.append(PageBreak())

    def _build_section_2_4_demand(self):
        def pluralize(count, singular, plural):
            return singular if count == 1 else plural

        results = self.results
        input_data = self.input_data
        nodes_df = self.nodes_df
        energy_flow_df = self.energy_flow_df
        custom_demand_df = self.custom_demand_df
        demand_ts = self.demand_ts

        self.elements.append(Paragraph("2.4 Demand Results", self.styles["Heading2"]))
        self.elements.append(Spacer(1, 24))

        if custom_demand_df.iloc[0].uploaded_data:
            self.elements.append(
                Paragraph(
                    "The demand estimation feature of the tool was not used. Instead, a time series was uploaded by the user.",
                    self.body_style,
                )
            )
            demand_ts = custom_demand_df.iloc[:, 0]
        else:
            consumers_df = nodes_df[nodes_df["Node type"] == "consumer"]
            n_households = consumers_df[
                consumers_df["Consumer type"] == "household"
            ].shape[0]
            n_enterprises = consumers_df[
                consumers_df["Consumer type"] == "enterprise"
            ].shape[0]
            n_public_services = consumers_df[
                consumers_df["Consumer type"] == "public_service"
            ].shape[0]

            self.elements.append(
                Paragraph(
                    f"A total of {n_households} {pluralize(n_households, 'household', 'households')}, "
                    f"{n_enterprises} {pluralize(n_enterprises, 'enterprise', 'enterprises')}, and "
                    f"{n_public_services} {pluralize(n_public_services, 'public service', 'public services')} were selected.",
                    self.body_style,
                )
            )

            consumer_counts = consumers_df.groupby(
                ["Consumer type", "Consumer detail"], dropna=False
            ).size()
            if not consumer_counts.empty:
                consumer_table_data = [["Consumer Type", "Detail", "Count"]]
                for (
                    consumer_type,
                    consumer_detail,
                ), count in consumer_counts.items():
                    detail_label = "-" if pd.isna(consumer_detail) else consumer_detail
                    consumer_table_data.append(
                        [consumer_type, detail_label, f"{count:,.0f}"]
                    )
                consumer_table = Table(consumer_table_data, colWidths=[150, 200, 100])
                consumer_table.setStyle(self.table_style)
                self.elements.append(consumer_table)
                self.elements.append(Spacer(1, 12))

            if "Demand [kW]" in energy_flow_df.columns:
                demand_ts = energy_flow_df["Demand [kW]"]

        yearly_demand = demand_ts.sum()
        num_hours = demand_ts.shape[0]
        full_year_hours = 8760

        demand_text = (
            f"The demand time series has a maximum load of {demand_ts.max():.2f} kW, "
            f"a minimum load of {demand_ts.min():.2f} kW, and an average load of {demand_ts.mean():.2f} kW. "
            f"The total annual demand is estimated to be {yearly_demand:.0f} kWh."
        )
        if num_hours < full_year_hours:
            demand_text += (
                f" Note: The original demand time series covered {num_hours} hours and has been scaled up "
                f"to represent a full year (8760 hours) for annual demand estimation."
            )
        self.elements.append(Paragraph(demand_text, self.body_style))

        if input_data.do_es_design_optimization:
            demand_kpi_text = (
                f"The peak demand is {results.peak_demand:,.1f} kW with a base load of {results.base_load:,.1f} kW. "
                f"The average annual demand per consumer is {results.average_annual_demand_per_consumer:,.0f} kWh, "
                f"and the total electricity surplus amounts to {self.surplus_total_kwh:,.0f} kWh/a."
            )
            self.elements.append(Paragraph(demand_kpi_text, self.body_style))

            if input_data.shortage_settings_is_selected:
                shortage_text = (
                    f"The total annual shortage amounts to {results.shortage_total:.1f}% of the demand, "
                    f"with a maximum shortage of {results.max_shortage:.1f}% in a single time step."
                )
                self.elements.append(Paragraph(shortage_text, self.body_style))

        if (
            not custom_demand_df.iloc[0].uploaded_data
            and input_data.do_demand_estimation
        ):
            self.elements.append(self.img_dict.get("demandTs"))
            self.elements.append(
                self._figure_caption("Figure: Demand Coverage of the Off-Grid System")
            )

        self.elements.append(PageBreak())

    def _build_section_2_5_environmental(self):
        results = self.results
        input_data = self.input_data

        if not input_data.do_es_design_optimization:
            return

        self.elements.append(
            Paragraph("2.5 Environmental Results", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 24))

        environmental_text = (
            f"The system achieves annual CO2 savings of {results.co2_savings:,.1f} t/a, compared to "
            f"annual CO2 emissions of {results.co2_emissions:,.1f} t/a. "
            f"The annual fuel consumption amounts to {results.fuel_consumption:,.0f} liters, and the "
            f"electricity surplus rate is {results.surplus_rate:.1f}%."
        )
        self.elements.append(Paragraph(environmental_text, self.body_style))

        self.elements.append(self.img_dict.get("demandCoverage"))
        self.elements.append(
            self._figure_caption(
                "Figure: Range by Renewable and Non-Renewable Resources"
            )
        )

    def _build_section_3_tool_description(self):
        self.elements.append(PageBreak())

        self.elements.append(Paragraph("3. Tool Description", self.styles["Heading1"]))
        self.elements.append(Spacer(1, 24))

        self.elements.append(
            Paragraph(
                "The tool systematically integrates geospatial data, demand forecasting, grid optimization, and generation system design to deliver optimized energy solutions. "
                "It begins by acquiring geolocation data of consumers through automatic detection using OpenStreetMap integration, manual selection via map markers, or direct input of geocoordinates. "
                "Users can then assign different types (households, public services or enterprises) to these geolocated consumers. "
                "This geospatial information forms the foundation for demand estimation and grid layout planning.",
                self.body_style,
            )
        )

        self.elements.append(
            Paragraph("3.1 Demand Estimation", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 12))
        self.elements.append(
            Paragraph(
                "For demand estimation, a predefined load profile is assigned to each consumer type in the background. "
                "This profile is based on processed load measurements of the specific consumer type. "
                "The total demand curve is then the accumulated load of all consumers.",
                self.body_style,
            )
        )

        self.elements.append(
            Paragraph("3.2 Grid Design Optimization", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 12))
        self.elements.append(
            Paragraph(
                "With both geolocation and demand data, the tool optimizes the spatial layout of the distribution grid. "
                "The tool adheres to constraints on grid allocation along roads, maximum connections per pole and maximum "
                "distances between consumers to ensure all consumers are effectively connected.",
                self.body_style,
            )
        )

        self.elements.append(
            Paragraph("3.3 Energy System Optimization", self.styles["Heading2"])
        )
        self.elements.append(Spacer(1, 12))
        self.elements.append(
            Paragraph(
                "In the generation system design phase, the tool integrates various energy converters, including photovoltaic systems and diesel generators, "
                "along with battery and hydrogen storage, inverters, and rectifiers. It models solar potential using ERA5 satellite data and PVLIB software. "
                "The optimization focuses on minimizing the Levelized Cost of Energy (LCOE) by considering both capital expenditures and operational costs. "
                "Formulating the problem as a mixed-integer linear model, the tool utilizes the open-source modeling framework OEMOF "
                "to find the optimal configuration that meets consumer demands.",
                self.body_style,
            )
        )
        self.elements.append(
            Paragraph(
                "Finally, the tool provides detailed outputs such as optimal installed capacities for each system component, time-series data of system operations, "
                "investment cost breakdowns, CO<sub>2</sub> emission estimates, and fuel consumption requirements. "
                "These results offer valuable insights for stakeholders to make informed decisions regarding the planning and implementation of off-grid energy solutions.",
                self.body_style,
            )
        )

    # ---- final assembly -----------------------------------------------------

    def _render(self):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
        )
        doc.title = "Offgridplanner"
        doc.author = "PeopleSuN"
        doc.subject = f"{self.input_data.name}"
        doc.keywords = "off-grid, energy, planning"

        doc.build(
            list(self.elements),
            onFirstPage=self._on_first_page,
            onLaterPages=self._add_page_number,
        )
        buffer.seek(0)
        return doc, buffer


def project_data_df_to_xlsx(  # noqa:PLR0913
    input_df,
    energy_system_design,
    energy_flow_df,
    results_df,
    nodes_df,
    links_df,
    currency,
):
    input_df, energy_flow_df, results_df, nodes_df, links_df = prepare_data_for_export(
        input_df,
        energy_system_design,
        energy_flow_df,
        results_df,
        nodes_df,
        links_df,
        currency,
    )
    excel_file = io.BytesIO()
    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        workbook = writer.book
        sheet1 = "results"
        results_df.to_excel(writer, sheet_name=sheet1, index=False)
        worksheet1 = writer.sheets[sheet1]
        format1 = workbook.add_format({"align": "left"})
        format2 = workbook.add_format({"align": "right"})
        col1_width = results_df.iloc[:, 0].astype(str).str.len().max()
        col2_width = results_df.iloc[:, 1].astype(str).str.len().max()
        col3_width = results_df.iloc[:, 2].astype(str).str.len().max()
        worksheet1.set_column(0, 0, col1_width, format1)
        worksheet1.set_column(1, 1, col2_width, format2)
        worksheet1.set_column(2, 2, col3_width, format1)
        sheet2 = "power time series"
        energy_flow_df.to_excel(writer, sheet_name=sheet2, index=False)
        writer.sheets[sheet2] = set_column_width(
            writer.sheets[sheet2],
            energy_flow_df,
            workbook.add_format({"align": "right"}),
        )
        sheet3 = "user specified input parameters"
        input_df.to_excel(writer, sheet_name=sheet3, index=False)
        worksheet3 = writer.sheets[sheet3]
        format1 = workbook.add_format({"align": "left"})
        format2 = workbook.add_format({"align": "right"})
        col1_width = input_df.iloc[:, 0].astype(str).str.len().max()
        col2_width = input_df.iloc[:, 1].astype(str).str.len().max()
        col3_width = input_df.iloc[:, 2].astype(str).str.len().max()
        worksheet3.set_column(0, 0, col1_width, format1)
        worksheet3.set_column(1, 1, col2_width, format2)
        worksheet3.set_column(2, 2, col3_width, format1)
        sheet4 = "nodes"
        nodes_df.to_excel(writer, sheet_name=sheet4, index=False)
        writer.sheets[sheet4] = set_column_width(
            writer.sheets[sheet4], nodes_df, workbook.add_format({"align": "right"})
        )
        sheet5 = "links"
        links_df.to_excel(writer, sheet_name=sheet5, index=False)
        writer.sheets[sheet5] = set_column_width(
            writer.sheets[sheet5], links_df, workbook.add_format({"align": "right"})
        )
    xlsx_data = excel_file.getvalue()
    return io.BytesIO(xlsx_data)


def set_column_width(worksheet, df, col_format=None):
    for i, col in enumerate(df.columns):
        column_len = df[col].astype(str).str.len().max()
        column_len = max(column_len, len(col)) + 2
        column_len = min(column_len, 150)
        if col_format:
            worksheet.set_column(i, i, column_len, col_format)
        else:
            worksheet.set_column(i, i, column_len)
    return worksheet
