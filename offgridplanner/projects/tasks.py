"""
This module in a FastAPI application uses Celery to handle asynchronous tasks:

1. `task_grid_opt`: Optimizes grid layouts for users and projects, with retry capabilities.
2. `task_supply_opt`: Optimizes energy supply systems for specific users and projects.
3. `task_remove_anonymous_users`: Deletes anonymous user accounts asynchronously.

Additionally, it includes functions to check the status of these tasks, identifying if they have completed, failed,
or been revoked. This setup enables efficient, asynchronous processing of complex tasks and user management.
"""
from celery import shared_task
from celery.result import AsyncResult

from offgridplanner.opt_models.grid_optimizer import optimize_grid
from offgridplanner.opt_models.supply_optimizer import optimize_energy_system
from offgridplanner.projects.models import Simulation


@shared_task
def hello():
    return 'hello world'

@shared_task(name='task_grid_opt',
             force=True,
             track_started=True,
             autoretry_for=(Exception,),
             retry_kwargs={'max_retries': 1, 'countdown': 10})
def task_grid_opt(proj_id):
    result = optimize_grid(proj_id)
    return result


@shared_task(name='task_supply_opt',
             force=True,
             track_started=True,
             autoretry_for=(Exception,),
             retry_kwargs={'max_retries': 1, 'countdown': 10}
             )
def task_supply_opt(proj_id):
    result = optimize_energy_system(proj_id)
    return result

def get_status(task_id):
    task = AsyncResult(task_id)
    status = task.state.lower()
    return status


def task_is_finished(task_id):
    status = get_status(task_id)
    if status in ['success', 'failure', 'revoked']:
        return True
    else:
        return False
