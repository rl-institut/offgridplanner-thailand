import json
import os

import numpy as np
import pandas as pd

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from offgridplanner.projects.forms import ProjectForm, CustomDemandForm, OptionForm
from offgridplanner.projects.models import Project, CustomDemand, Nodes
from offgridplanner.projects.demand_estimation import get_demand_timeseries, LOAD_PROFILES


@require_http_methods(["GET"])
def home(request):
    return render(
        request,
        "pages/landing_page.html",
        {"step_list": STEPS.keys()},
    )


# @login_required()
@require_http_methods(["GET"])
def project_setup(request, proj_id=None):
    form = ProjectForm()
    context = {"form": form}
    if proj_id is not None:
        max_days = int(os.environ.get("MAX_DAYS", 365))
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
        context = {"opts_form": form, "project_id": project.id, "max_days": max_days}

    # TODO in the js figure out what this is supposed to mean, this make the next button jump to either step 'consumer_selection'
    # or step 'demand_estimation'
    # const consumerSelectionHref = `consumer_selection?project_id=${project_id}`;
    # const demandEstimationHref = `demand_estimation?project_id =${project_id}`;
    # If Consumer Selection is hidden (in raw html), go to demand_estimation

    return render(request, "pages/project_setup.html", context)


# @login_required()
@require_http_methods(["GET"])
def consumer_selection(request, proj_id=None):
    form = ProjectForm()
    opts = OptionForm()

    public_service_list = {
        "group1": "Health_Health Centre",
        "group2": "Health_Clinic",
        "group3": "Health_CHPS",
        "group4": "Education_School",
        "group5": "Education_School_noICT",
    }

    enterprise_list = {
        "group1": "Food_Groceries",
        "group2": "Food_Restaurant",
        "group3": "Food_Bar",
        "group4": "Food_Drinks",
        "group5": "Food_Fruits or vegetables",
        "group6": "Trades_Tailoring",
        "group7": "Trades_Beauty or Hair",
        "group8": "Trades_Metalworks",
        "group9": "Trades_Car or Motorbike Repair",
        "group10": "Trades_Carpentry",
        "group11": "Trades_Laundry",
        "group12": "Trades_Cycle Repair",
        "group13": "Trades_Shoemaking",
        "group14": "Retail_Medical",
        "group15": "Retail_Clothes and accessories",
        "group16": "Retail_Electronics",
        "group17": "Retail_Other",
        "group18": "Retail_Agricultural",
        "group19": "Digital_Mobile or Electronics Repair",
        "group20": "Digital_Digital Other",
        "group21": "Digital_Cybercafé",
        "group22": "Digital_Cinema or Betting",
        "group23": "Digital_Photostudio",
        "group24": "Agricultural_Mill or Thresher or Grater",
        "group25": "Agricultural_Other",
    }

    enterpise_option = ""

    large_load_list = {
        "group1": "Milling Machine (7.5kW)",
        "group2": "Crop Dryer (8kW)",
        "group3": "Thresher (8kW)",
        "group4": "Grinder (5.2kW)",
        "group5": "Sawmill (2.25kW)",
        "group6": "Circular Wood Saw (1.5kW)",
        "group7": "Jigsaw (0.4kW)",
        "group8": "Drill (0.4kW)",
        "group9": "Welder (5.25kW)",
        "group10": "Angle Grinder (2kW)",
    }
    large_load_type = "group1"

    option_load = ""

    context = {
        "form": form,
        "opts_form": opts,
        "public_service_list": public_service_list,
        "enterprise_list": enterprise_list,
        "large_load_list": large_load_list,
        "large_load_type": large_load_type,
        "enterpise_option": enterpise_option,
        "option_load": option_load,
    }
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
        context["proj_id"] = project.id
    else:
        project = Project.objects.first()
        context["proj_id"] = project.id

    # _wizard.js contains info for the POST function set when clicking on next or on another step

    return render(request, "pages/consumer_selection.html", context)


# @login_required()
@require_http_methods(["GET"])
def demand_estimation(request, proj_id=None):
    if proj_id is not None:
        project = get_object_or_404(Project, id=proj_id)
        if project.user != request.user:
            raise PermissionDenied
    # TODO delete
    else:
        project = Project.objects.first()
        proj_id = project.id

    custom_demand, _ = CustomDemand.objects.get_or_create(project__id=proj_id)

    form = CustomDemandForm(instance=custom_demand)
    context = {"form": form, "proj_id": proj_id}

    # nodes = project.nodes
    # demand_timeseries = get_demand_timeseries(nodes, custom_demand)

    return render(request, "pages/demand_estimation.html", context)


# @login_required()
@require_http_methods(["GET"])
def grid_design(request):
    return render(request, "pages/grid_design.html")


# @login_required()
@require_http_methods(["GET"])
def energy_system_design(request):
    return render(request, "pages/energy_system_design.html")


# @login_required()
@require_http_methods(["GET"])
def simulation_results(request):
    return render(request, "pages/simulation_results.html")


STEPS = {
    "project_setup": project_setup,
    "consumer_selection": consumer_selection,
    "demand_estimation": demand_estimation,
    "grid_design": grid_design,
    "energy_system_design": energy_system_design,
    "simulation_results": simulation_results,
}


# @login_required
@require_http_methods(["GET", "POST"])
def steps(request, proj_id, step_id=None):
    if step_id is None:
        return HttpResponseRedirect(reverse("steps", args=[proj_id, 1]))

    return STEPS[step_id - 1](request, proj_id, step_id)
