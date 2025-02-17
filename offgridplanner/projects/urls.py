from django.urls import path

from .views import *

app_name = "projects"

urlpatterns = [
    path("", projects_list, name="projects_list"),
    path("duplicate/<int:proj_id>", project_duplicate, name="project_duplicate"),
    path("delete/<int:proj_id>", project_delete, name="project_delete"),
    path(
        "add_buildings_inside_boundary/<int:proj_id>",
        add_buildings_inside_boundary,
        name="add_buildings_inside_boundary",
    ),
    path(
        "remove_buildings_inside_boundary/<int:proj_id>",
        remove_buildings_inside_boundary,
        name="remove_buildings_inside_boundary",
    ),
    path("consumer_to_db", consumer_to_db, name="consumer_to_db"),
    path("consumer_to_db/<int:proj_id>", consumer_to_db, name="consumer_to_db"),
    path("db_links_to_js/<int:proj_id>", db_links_to_js, name="db_links_to_js"),
    path("file_nodes_to_js", file_nodes_to_js, name="file_nodes_to_js"),
    path("db_nodes_to_js", db_nodes_to_js, name="db_nodes_to_js"),
    path("db_nodes_to_js/<int:proj_id>", db_nodes_to_js, name="db_nodes_to_js"),
    path(
        "db_nodes_to_js/<int:proj_id>/<int:markers_only>",
        db_nodes_to_js,
        name="db_nodes_to_js",
    ),
    path("load-demand-plot-data/<int:proj_id>", load_demand_plot_data, name="load_demand_plot_data"),
]
