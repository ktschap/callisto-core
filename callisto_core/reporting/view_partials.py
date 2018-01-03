'''

View partials provide all the callisto-core front-end functionality.
Subclass these partials with your own views if you are implementing
callisto-core. Many of the view partials only provide a subset of the
functionality required for a full HTML view.

docs / reference:
    - https://docs.djangoproject.com/en/1.11/topics/class-based-views/

view_partials should define:
    - forms
    - models
    - helper classes
    - access checks
    - redirect handlers

and should not define:
    - templates
    - url names

'''
from django.contrib.auth.views import PasswordResetView
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import ModelFormMixin

from callisto_core.accounts import (
    forms as account_forms, tokens as account_tokens,
)
from callisto_core.delivery import view_partials as delivery_partials
from callisto_core.utils.api import MatchingApi, NotificationApi, TenantApi

from . import forms, validators, view_helpers


class SubmissionPartial(
    view_helpers.ReportingSuccessUrlMixin,
    delivery_partials.ReportUpdatePartial,
):
    back_url = None
    EVAL_ACTION_TYPE = 'SUBMISSION'

    @property
    def coordinator_emails(self):
        return TenantApi.site_settings(
            'COORDINATOR_EMAIL', request=self.request)

    @property
    def coordinator_public_key(self):
        return TenantApi.site_settings(
            'COORDINATOR_PUBLIC_KEY', request=self.request)


class SchoolEmailFormPartial(
    SubmissionPartial,
    PasswordResetView,
):
    form_class = account_forms.ReportingVerificationEmailForm
    token_generator = account_tokens.StudentVerificationTokenGenerator()
    # success_url is used for inputting a valid school email address
    success_url = None
    # next_url is used for having your account already verified,
    # and inputting a correct account verification token
    next_url = None
    EVAL_ACTION_TYPE = 'SCHOOL_EMAIL'

    def dispatch(self, request, *args, **kwargs):
        if self.email_is_verified():
            return self._redirect_to_next()
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(self.success_url)

    def form_valid(self, form):
        '''
        avoid saving the form twice (and thus sending emails twice)
        '''
        return ModelFormMixin.form_valid(self, form)

    def email_is_verified(self):
        return self.request.user.account.is_verified

    def _redirect_to_next(self):
        next_url = reverse(
            self.next_url,
            kwargs={'uuid': self.report.uuid},
        )
        return redirect(next_url)


class SchoolEmailConfirmationPartial(
    SchoolEmailFormPartial,
):

    def verify_email(self):
        self.request.user.account.is_verified = True
        self.request.user.account.save()

    def dispatch(self, request, token=None, uidb64=None, *args, **kwargs):
        if self.token_generator.check_token(self.request.user, token):
            self.verify_email()
            return self._redirect_to_next()
        else:
            return super().dispatch(self.request, *args, **kwargs)


class PrepPartial(
    SubmissionPartial,
):
    form_class = forms.PrepForm
    EVAL_ACTION_TYPE = 'CONTACT_PREP'


class ReportSubclassPartial(
    SubmissionPartial,
):

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'instance': None})  # TODO: remove
        return kwargs


class MatchingPartial(
    ReportSubclassPartial,
):
    matching_validator_class = validators.Validators
    EVAL_ACTION_TYPE = 'ENTER_MATCHING'

    def get_matching_validators(self, *args, **kwargs):
        return self.matching_validator_class()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'matching_validators': self.get_matching_validators()})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        identifier = form.cleaned_data.get('identifier')
        matches = self._get_matches(identifier)

        self._notify_owner_of_submission(identifier)
        self._notify_authority_of_matches(matches, identifier)
        self._notify_owners_of_matches(matches)

        return response

    def _get_matches(self, identifier):
        return MatchingApi.find_matches(identifier)

    def _notify_owner_of_submission(self, identifier):
        if identifier:
            NotificationApi.send_confirmation(
                email_type='match_confirmation',
                to_addresses=[self.report.contact_email],
                site_id=self.site_id,
            )

    def _notify_authority_of_matches(self, matches, identifier):
        if matches:
            NotificationApi.send_matching_report_to_authority(
                matches=matches,
                identifier=identifier,
                to_addresses=self.coordinator_emails,
                public_key=self.coordinator_public_key,
            )

    def _notify_owners_of_matches(self, matches):
        for match in matches:
            NotificationApi.send_match_notification(
                match_report=match,
            )


class OptionalMatchingPartial(
    MatchingPartial,
):
    form_class = forms.MatchingOptionalForm


class RequiredMatchingPartial(
    MatchingPartial,
):
    form_class = forms.MatchingRequiredForm


class ConfirmationPartial(
    ReportSubclassPartial,
):
    form_class = forms.ConfirmationForm
    EVAL_ACTION_TYPE = 'REPORTING'

    def form_valid(self, form):
        output = super().form_valid(form)
        self._save_to_address(form)
        self._send_report_emails()
        return output

    def _send_report_to_authority(self, report):
        NotificationApi.send_report_to_authority(
            sent_report=report,
            report_data=self.storage.cleaned_form_data,
            site_id=self.site_id,
            to_addresses=self.coordinator_emails,
            public_key=self.coordinator_public_key,
        )

    def _send_confirmation_email(self):
        NotificationApi.send_confirmation(
            email_type='submit_confirmation',
            to_addresses=[self.report.contact_email],
            site_id=self.site_id,
        )

    def _save_to_address(self, form):
        sent_report = form.instance
        sent_report.to_address = self.coordinator_emails
        sent_report.save()

    def _send_report_emails(self):
        for sent_full_report in self.report.sentfullreport_set.all():
            self._send_report_to_authority(sent_full_report)
        self._send_confirmation_email()


class MatchingWithdrawPartial(
    view_helpers.ReportingSuccessUrlMixin,
    delivery_partials.ReportActionPartial,
):
    EVAL_ACTION_TYPE = 'MATCHING_WITHDRAW'

    def view_action(self):
        self.report.withdraw_from_matching()
