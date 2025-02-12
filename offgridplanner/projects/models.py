import datetime

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models


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
        return f"Project {self.id} -: {self.name}"

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
    status = models.CharField(max_length=25, default="not yet started")

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

class Nodes(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True)
    data = models.JSONField()
