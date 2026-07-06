from django.forms import RadioSelect


class OptimizeComponentWidget(RadioSelect):
    template_name = "widgets/optimize_component_widget.html"

    class Media:
        js = "js/energy-system-design.js"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "onchange": f"check_optimization_strategy('{self.attrs.get('component', '')}')"
            }
        )
