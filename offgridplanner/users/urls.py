from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import signup, activate

app_name = "users"
urlpatterns = [
    path("signup/", view=signup, name="account_signup"),
    path("activate/<uidb64>/<token>/", activate, name="activate"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]
