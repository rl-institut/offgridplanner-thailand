from __future__ import annotations

import os
import smtplib
import typing
import warnings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core import context
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext_lazy as _

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

    from offgridplanner.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        request = globals()["context"].request
        ctx = {
            "request": request,
            "email": email,
            "current_site": get_current_site(request),
        }
        ctx.update(context)
        msg = self.render_mail(template_prefix, email, ctx)
        if settings.USE_CUSTOM_SENDMAIL is True:
            self.send_custom_mail(
                to_email=msg.to,
                subject=msg.subject,
                message=msg.body,
            )
        else:
            msg.send()

    def send_custom_mail(self, to_email, subject, message):
        """Send E-mail via office365 Server using credentials from env vars
        Parameters
        ----------
        to_email : :obj:`str`
            Target mail address
        subject : :obj:`str`
            Subject of mail
        message : :obj:`str`
            Message body of mail

        Raises
        ------
        smtplib.SMTPAuthenticationError
            If authentication with the SMTP server fails.
        Exception
            If any other error occurs during the SMTP connection or sending process.
        Notes
        -----
        The following environment variables must be defined:
            - DEFAULT_FROM_EMAIL: The sender's email address.
            - EMAIL_HOST: The SMTP host (e.g., smtp.office365.com).
            - EMAIL_HOST_USER: The SMTP login username.
            - EMAIL_HOST_PASSWORD: The SMTP login password.
        """
        _message = MIMEMultipart()
        _message["From"] = os.environ.get("DEFAULT_FROM_EMAIL")
        _message["To"] = ",".join(to_email)
        _message["Subject"] = subject
        _message.attach(MIMEText(message, "plain"))
        with smtplib.SMTP(os.environ.get("EMAIL_HOST"), 587) as server:
            server.starttls()
            try:
                server.login(
                    os.environ.get("EMAIL_HOST_USER"),
                    os.environ.get("EMAIL_HOST_PASSWORD"),
                )
                server.sendmail(
                    os.environ.get("DEFAULT_FROM_EMAIL"),
                    to_email,
                    _message.as_string(),
                )

            except smtplib.SMTPAuthenticationError as e:
                err_msg = (
                    _("Form - mail sending error:")
                    + f" {e}"
                    + f", {os.environ.get('DEFAULT_FROM_EMAIL').replace('@', '')}"
                )
                warnings.warn(err_msg, stacklevel=2, category=UserWarning)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict[str, typing.Any],
    ) -> User:
        """
        Populates user information from social provider info.

        See: https://docs.allauth.org/en/latest/socialaccount/advanced.html#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"
        return user
