import os
import io
import json
from collections import defaultdict

import numpy as np

from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, StreamingHttpResponse
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages

# from jsonview.decorators import json_view
import pandas as pd
from offgridplanner.projects.demand_estimation import get_demand_timeseries, LOAD_PROFILES
from offgridplanner.projects.helpers import check_imported_consumer_data, consumer_data_to_file, load_project_from_dict

from offgridplanner.projects.models import Project, Nodes, CustomDemand
from offgridplanner.users.models import User
from offgridplanner.projects import identify_consumers_on_map

# @login_required
@require_http_methods(["GET"])
def projects_list(request, proj_id=None):
    projects= Project.objects.all()
    # projects = (
    #     Project.objects.filter(
    #         Q(user=request.user) | Q(viewers__user__email=request.user.email)
    #     )
    #     .distinct()
    #     .order_by("date_created")
    #     .reverse()
    # )
    for project in projects:
        # TODO this should not be useful
        # project.created_at = project.created_at.date()
        # project.updated_at = project.updated_at.date()
        if bool(os.environ.get('DOCKERIZED')):
            status = "pending"  #TODO connect this to the worker
            # status = worker.AsyncResult(user.task_id).status.lower()
        else:
            status = 'success'
        if status in ['success', 'failure', 'revoked']:
            # TODO this is not useful
            # user.task_id = ''
            # user.project_id = None
            if status == 'success':
                # TODO Here I am not sure we should use the status of the project rather the one of the simulation
                project.status = "finished"
            else:
                project.status = status
            # TODO this is not useful
            # user.task_id = ''
            # user.project_id = None

    return render(request, "pages/user_projects.html", {"projects": projects})


@require_http_methods(["GET","POST"])
def project_duplicate(request, proj_id):
    # proj_id = None  # TODO remove this when project is fixed
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    else:
        project = Project.objects.first()  # TODO remove this when project is fixed

    # TODO check user rights to the project
    dm = project.export()
    user = User.objects.get(email=request.user.email)
    # TODO must find user from its email address
    new_proj_id = load_project_from_dict(dm, user=user)


    # for model_class in [sa_tables.Nodes, sa_tables.Links, sa_tables.Results, sa_tables.DemandCoverage,
    #                     sa_tables.EnergyFlow,
    #                     sa_tables.Emissions, sa_tables.DurationCurve, sa_tables.ProjectSetup,
    #                     sa_tables.EnergySystemDesign,
    #                     sa_tables.GridDesign, sa_tables.Demand]:
    #     model_instance = await get_model_instance(model_class, user_from_id, project_from_id, 'all')
    #     if model_class == sa_tables.ProjectSetup:
    #         time_now = datetime.datetime.now()
    #         time_now \
    #             = datetime.datetime(time_now.year, time_now.month, time_now.day, time_now.hour, time_now.minute)
    #         model_instance[0].created_at = time_now
    #         model_instance[0].updated_at = time_now
    #         model_instance[0].project_name = 'Copy of {}'.format(
    #             model_instance[0].project_name.replace("Exmaple", "Example"))
    #         if model_instance[0].project_name == "Copy of Example Project":
    #             model_instance[0].project_name = "Example Project"
    #     for e in model_instance:
    #         data = {key: value for key, value in e.__dict__.items() if not key.startswith('_')}
    #         new_e = model_class(**data)
    #         new_e.id = user_to_id
    #         new_e.project_id = project_to_id
    #         await merge_model(new_e)
    # return JsonResponse({'success': True},status=200)
    # if user is not None and project_id is not None:
    #     # TODO copy project here
    #     return JSONResponse(status_code=200, content={'success': True})
    # else:
    #     return JSONResponse(status_code=400, content={'success': False})
    return HttpResponseRedirect(reverse("projects:projects_list"))
    # return HttpResponseRedirect(reverse("projects:projects_list", args=[new_proj_id]))

@require_http_methods(["POST"])
def project_delete(request, proj_id):
    project = get_object_or_404(Project, id=proj_id)

    if project.user != request.user:
        raise PermissionDenied

    if request.method == "POST":
        project.delete()
        # message not defined
        messages.success(request, "Project successfully deleted!")

    return HttpResponseRedirect(reverse("projects:projects_list"))




# TODO should be used as AJAX from map
@require_http_methods(["POST"])
def add_buildings_inside_boundary(request, proj_id):
    proj_id = None # TODO remove this when project is fixed
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    else:
        project = Project.objects.first() # TODO remove this when project is fixed

    js_data = json.loads(request.body)
    # js_datapydantic_schema.MapData consists of
    #     boundary_coordinates: list
    #     map_elements: list

    boundary_coordinates = js_data["boundary_coordinates"][0][0]
    df = pd.DataFrame.from_dict(boundary_coordinates).rename(columns={'lat': 'latitude', 'lng': 'longitude'})
    if df['latitude'].max() - df['latitude'].min() > float(os.environ.get("MAX_LAT_LON_DIST", 0.15)):
        return JsonResponse({'executed': False,
                             'msg': 'The maximum latitude distance selected is too large. '
                                    'Please select a smaller area.'})
    elif df['longitude'].max() - df['longitude'].min() > float(os.environ.get("MAX_LAT_LON_DIST", 0.15)):
        return JsonResponse({'executed': False,
                             'msg': 'The maximum longitude distance selected is too large. '
                                    'Please select a smaller area.'})
    data, building_coordinates_within_boundaries = identify_consumers_on_map.get_consumer_within_boundaries(df)
    if not building_coordinates_within_boundaries:
        return JsonResponse({'executed': False, 'msg': 'In the selected area, no buildings could be identified.'})
    nodes = defaultdict(list)
    for label, coordinates in building_coordinates_within_boundaries.items():
        nodes["latitude"].append(round(coordinates[0], 6))
        nodes["longitude"].append(round(coordinates[1], 6))
        nodes["how_added"].append("automatic")
        nodes["node_type"].append("consumer")
        nodes["consumer_type"].append('household')
        nodes["consumer_detail"].append('default')
        nodes['custom_specification'].append('')
        nodes['shs_options'].append(0)
        nodes['is_connected'].append(True)
    # if user.email.split('__')[0] == 'anonymous':
    #     max_consumer = int(os.environ.get("MAX_CONSUMER_ANONYMOUS", 150))
    # else:
    max_consumer = int(os.environ.get("MAX_CONSUMER", 1000))
    if len(nodes['latitude']) > max_consumer:
        return JsonResponse({'executed': False,
                             'msg': 'You have selected {} consumers. You can select a maximum of {} consumer. '
                                    'Reduce the number of consumers by selecting a small area, for example.'
                            .format(len(data['elements']), max_consumer)})
    df = pd.DataFrame.from_dict(nodes)
    df['is_connected'] = df['is_connected']
    df_existing = pd.DataFrame.from_records(js_data["map_elements"])
    df = pd.concat([df_existing, df], ignore_index=True)
    df = df.drop_duplicates(subset=['longitude', 'latitude'], keep='first')
    df['shs_options'] = df['shs_options'].fillna(0)
    df['custom_specification'] = df['custom_specification'].fillna('')
    df['is_connected'] = df['is_connected'].fillna(True)
    nodes_list = df.to_dict('records')
    return JsonResponse({'executed': True, 'msg': '', 'new_consumers': nodes_list})


# TODO should be used as AJAX from backend_communication.js
@require_http_methods(["POST"])
def remove_buildings_inside_boundary(request, proj_id=None):  # data: pydantic_schema.MapData
    data = json.loads(request.body)
    df = pd.DataFrame.from_records(data["map_elements"])
    if not df.empty:
        boundaries = pd.DataFrame.from_records(data["boundary_coordinates"][0][0]).values.tolist()
        df['inside_boundary'] = identify_consumers_on_map.are_points_in_boundaries(df, boundaries=boundaries, )
        df = df[df['inside_boundary'] == False]
        df = df.drop(columns=['inside_boundary'])
        return JsonResponse({'map_elements': df.to_dict('records')})

# TODO this seems like an old unused view
@require_http_methods(["GET"])
def db_links_to_js(request, proj_id):
    proj_id = None  # TODO remove this when project is fixed
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    else:
        project=Project.objects.first()# TODO remove this when project is fixed

        # links = Links.objects.filter(project=project).first()
        links = None
        links_json = json.loads(links.data) if links is not None else json.loads('{}')
        return JsonResponse(links_json, status=200)


# @json_view
@require_http_methods(["GET"])
def db_nodes_to_js(request, proj_id=None, markers_only=False):
    proj_id = None  # TODO remove this when project is fixed
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    else:
        project = Project.objects.first()  # TODO remove this when project is fixed
        nodes = Nodes.objects.get(project=project)
        df = pd.read_json(nodes.data) if nodes is not None else pd.DataFrame()
        if not df.empty:
            df = df[
                [
                    "latitude",
                    "longitude",
                    "how_added",
                    "node_type",
                    "consumer_type",
                    "consumer_detail",
                    "custom_specification",
                    "is_connected",
                    "shs_options",
                ]
            ]
            power_house = df[df["node_type"] == "power-house"]
            if markers_only is True:
                if len(power_house) > 0 and power_house["how_added"].iat[0] == "manual":
                    df = df[df["node_type"].isin(["power-house", "consumer"])]
                else:
                    df = df[df["node_type"] == "consumer"]
            df["latitude"] = df["latitude"].astype(float)
            df["longitude"] = df["longitude"].astype(float)
            df["shs_options"] = df["shs_options"].fillna(0)
            df["custom_specification"] = df["custom_specification"].fillna("")
            df["shs_options"] = df["shs_options"].astype(int)
            df["is_connected"] = df["is_connected"].astype(bool)
            nodes_list = df.to_dict("records")
            is_load_center = True
            if (
                len(power_house.index) > 0
                and power_house["how_added"].iat[0] == "manual"
            ):
                is_load_center = False
            return JsonResponse(
                status=200,
                content={"is_load_center": is_load_center, "map_elements": nodes_list},
            )

@require_http_methods(["POST"])
# async def consumer_to_db(request, proj_id):
def consumer_to_db(request, proj_id=None):
    proj_id = None # TODO remove this when project is fixed
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    else:
        project = Project.objects.first() # TODO remove this when project is fixed
        data = json.loads(request.body)
        print(data["map_elements"])

        df = pd.DataFrame.from_records(data["map_elements"])
        if df.empty is True:
            Nodes.objects.filter(project=project).delete()
            return
        df = df.drop_duplicates(subset=['latitude', 'longitude'])
        drop_index = df[df['node_type'] == 'power-house'].index
        if len(drop_index) > 1:
            df = df.drop(index=drop_index[1:])
        if df.empty is True:
            Nodes.objects.filter(project=project).delete()
            return
        df = df[df['node_type'].isin(['power-house', 'consumer'])]
        if df.empty is True:
            Nodes.objects.filter(project=project).delete()
            return
        df = df[['latitude', 'longitude', 'how_added', 'node_type', 'consumer_type', 'custom_specification', 'shs_options', 'consumer_detail']]
        df['consumer_type'] = df['consumer_type'].fillna('household')
        df['custom_specification'] = df['custom_specification'].fillna('')
        df['shs_options'] = df['shs_options'].fillna(0)
        df['is_connected'] = True
        df = df.round(decimals=6)
        if df.empty:
            Nodes.objects.filter(project=project).delete()
            return
        df["node_type"] = df["node_type"].astype(str)
        if len(df.index) != 0:
            if 'parent' in df.columns:
                df['parent'] = df['parent'].replace('unknown', None)
        df.latitude = df.latitude.map(lambda x: "%.6f" % x)
        df.longitude = df.longitude.map(lambda x: "%.6f" % x)
        if data["file_type"] == 'db':
            nodes = Nodes()
            nodes.project = project
            nodes.data=df.reset_index(drop=True).to_json()
            nodes.save()

            return JsonResponse({"message": "Success"},status=200)
        else:
            io_file = consumer_data_to_file(df, data["file_type"])
            if data["file_type"] == 'xlsx':
                response = StreamingHttpResponse(io_file,
                                             # media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                                )
                response.headers["Content-Disposition"] = "attachment; filename=offgridplanner_consumers.xlsx"
            elif data["file_type"] == 'csv':
                response = StreamingHttpResponse(io_file,
                                             # media_type="text/csv"
                                                 )
                response.headers["Content-Disposition"] = "attachment; filename=offgridplanner_consumers.csv"
            return response


@require_http_methods(["POST"])
# async def file_nodes_to_js(file):  # UploadFile = File(...)
def file_nodes_to_js(request):  # UploadFile = File(...)
    file = request.FILES["file"]
    filename = file.name
    file_extension = filename.split(".")[-1].lower()
    if file_extension not in ["csv", "xlsx"]:
        raise HttpResponse(
            status=400,
            reason="Unsupported file type. Please upload a CSV or Excel file.",
        )
    try:
        if file_extension == "csv":
            file_content = file.read()
            # file_content = await file.read()
            decoded_content = file_content.decode("utf-8")
            df = pd.read_csv(io.StringIO(decoded_content))
        elif file_extension == "xlsx":
            df = pd.read_excel(io.BytesIO(file.read()), engine="openpyxl")
            # df = pd.read_excel(io.BytesIO(await file.read()), engine='openpyxl')
        if not df.empty:
            print(df)
            try:
                df, msg = check_imported_consumer_data(df)
                if df is None and msg is not None:
                    return JsonResponse({"responseMsg": msg}, status=200)
            except Exception as e:
                err_msg = str(e)
                msg = f"Failed to import file. Internal error message: {err_msg}"
                return JsonResponse({"responseMsg": msg}, status=200)
            return JsonResponse(
                data={"is_load_center": False, "map_elements": df.to_dict("records")},
                status=200,
            )
    except Exception as e:
        raise HttpResponse(status=500, reason=f"Failed to process the file: {e}")


def load_demand_plot_data(request, proj_id=None):
    # if is_ajax(request):
    time_range = range(0, 24)
    nodes = Nodes.objects.get(project__id=proj_id)
    custom_demand = CustomDemand.objects.get(project__id=proj_id)
    demand_df = get_demand_timeseries(nodes, custom_demand, time_range=time_range)
    load_profiles = LOAD_PROFILES.iloc[time_range].copy()

    timeseries = {
        'x': demand_df.index.tolist(),
        'households': demand_df.household.tolist(),
        'enterprises': demand_df.enterprise.tolist(),
        'public_services': demand_df.public_service.tolist(),
        'Average': np.zeros(len(time_range))
    }

    for tier in ["very_low", "low", "middle","high", "very_high"]:
        tier_verbose = f"{tier.title().replace('_', ' ')} Consumption"
        profile_col = f"Household_Distribution_Based_{tier_verbose}"
        timeseries[tier_verbose] = load_profiles[profile_col].values.tolist()
        timeseries["Average"] = np.add(getattr(custom_demand, tier) * np.array(load_profiles[profile_col].values.tolist()), timeseries["Average"])

    timeseries["Average"] = timeseries["Average"].tolist()
    return JsonResponse({"timeseries": timeseries}, status=200)
