from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect
from django.db.models import QuerySet
from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from offgridplanner.users.forms import UserSignupForm
from offgridplanner.users.models import User
from offgridplanner.users.services import send_mail

UserModel = get_user_model()


def signup(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            subject = _("Activate your account.")
            protocol = "https" if settings.DEBUG is False else request.scheme

            message = render_to_string(
                "account/acc_active_email.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": default_token_generator.make_token(user),
                    "protocol": protocol,
                },
            )
            print(message)
            to_email = form.cleaned_data.get("email")
            # send_mail(to_address=to_email, msg=message, subject=subject)
            # TODO some encode error here
            messages.info(
                request,
                _(
                    "Please confirm your email address to complete the registration  (note that the registration email may land in your spam box, if your email provider does not trust our domain name, we have unfortunately no control on our users' email provider)"
                ),
            )
            return redirect("home")
    else:
        form = UserSignupForm(privacy_url=reverse("privacy"))
    return render(request, "account/signup.html", {"form": form})


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(
            request,
            _(
                "Thank you for your email confirmation. Now you can log in your account."
            ),
        )
        return redirect("account_login")
    else:
        return HttpResponse("Activation link is invalid!")
        return redirect("home")


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()
