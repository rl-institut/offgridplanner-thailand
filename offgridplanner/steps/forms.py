from django.forms import ModelForm

from offgridplanner.projects.helpers import csv_to_dict
from offgridplanner.steps.models import CustomDemand, GridDesign

FORM_FIELD_METADATA = csv_to_dict("data/form_parameters.csv")


def set_field_metadata(field, meta):
    field.label = meta.get("verbose", field.label.title())  # Set verbose name
    field.help_text = meta.get("help_text", "")  # Set help text
    field.widget.attrs["unit"] = meta.get("unit", "")  # Store unit as an attribute
    return


class CustomDemandForm(ModelForm):
    percentage_fields = ["very_low", "low", "middle", "high", "very_high"]

    class Meta:
        model = CustomDemand
        exclude = ["project", "uploaded_data"]

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        instance = kwargs.get("instance")

        if instance is not None:
            for field in self.percentage_fields:
                # Serve number to user in 0-100 format
                initial[field] = self.change_percentage_format(
                    getattr(instance, field),
                    upper_limit=100,
                )

            kwargs["initial"] = initial

        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name in FORM_FIELD_METADATA:
                meta = FORM_FIELD_METADATA[field_name]
                set_field_metadata(field, meta)

    def clean(self):
        cleaned_data = super().clean()
        percentage_values = {
            field: cleaned_data[field] for field in self.percentage_fields
        }
        total = round(sum(percentage_values.values(), 0))
        if total != 1:
            # TODO tbd how we want to handle this
            # raise ValidationError("The sum of all shares must equal 100%.")
            print("The sum of all shares does not equal 100%.")

        for field, value in self.cleaned_data.items():
            if field in self.percentage_fields:
                # Save number to database in 0-1 format
                self.cleaned_data[field] = self.change_percentage_format(
                    value,
                    upper_limit=1,
                )

        return cleaned_data

    @staticmethod
    def change_percentage_format(value, upper_limit=1):
        # Changes the value from a percentage range 0-1 to 0-100 and viceversa
        if upper_limit == 1:
            value /= 100.0
        elif upper_limit == 100:
            value *= 100
        else:
            raise ValueError("Upper limit must be either 1 or 100")

        return value


class GridDesignForm(ModelForm):
    class Meta:
        model = GridDesign
        exclude = ["project"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name in FORM_FIELD_METADATA:
                model_field = self._meta.model._meta.get_field(field_name)
                # Set the db_column name as an attribute (important for splitting by double underscores in the view)
                field.db_column = model_field.db_column
                meta = FORM_FIELD_METADATA[field_name]
                set_field_metadata(field, meta)
