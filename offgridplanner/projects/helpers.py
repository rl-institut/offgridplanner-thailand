import io

from offgridplanner.projects.models import Options
from offgridplanner.projects.models import Project


def load_project_from_dict(model_data, user=None):
    """Create a new project for a user

    Parameters
    ----------
    model_data: dict
        output produced by the export() method of the Project model
    user: users.models.CustomUser
        the user which loads the scenario
    """
    options_data_dm = model_data.pop("options_data", None)

    model_data["user"] = user
    if options_data_dm is not None:
        options_data = Options(**options_data_dm)
        options_data.save()
        model_data["options"] = options_data
    project = Project(**model_data)
    project.save()

    return project.id


def df_to_file(df, file_type):
    if file_type == "xlsx":
        output = io.BytesIO()
        df.to_excel(output, index=False, engine="xlsxwriter")
        output.seek(0)
        return io.BytesIO(output.getvalue())
    if file_type == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return io.StringIO(output.getvalue())


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"
