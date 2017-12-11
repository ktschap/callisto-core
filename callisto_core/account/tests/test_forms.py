from config.tests.base import CallistoTestCase
from tenants.models import Tenant

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test.utils import override_settings

from ..forms import SendVerificationEmailForm
from ..validators import non_school_email_error

User = get_user_model()


class MockView(object):

    def __init__(self, test):
        self.request = test.request


class StudentVerificationTest(CallistoTestCase):

    def setUp(self):
        super().setUp()
        self.request = HttpRequest()
        self.request.method = 'POST'
        self.request.META['HTTP_HOST'] = 'testserver'
        self.request.tenant = Tenant.objects.get(site_id=1)

    def test_student_email_accepted(self):
        good_data = {'email': 'myname@projectcallisto.org'}
        form = SendVerificationEmailForm(good_data, view=MockView(self))
        self.assertTrue(form.is_valid())

    def test_subdomain_not_accepted(self):
        bad_data = {'email': 'myname@cats.projectcallisto.org'}
        form = SendVerificationEmailForm(bad_data, view=MockView(self))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['email'],
            [non_school_email_error(self.request)]
        )

    def test_partial_not_accepted(self):
        bad_data = {'email': 'projectcallisto.edu@gmail.com'}
        form = SendVerificationEmailForm(bad_data, view=MockView(self))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['email'],
            [non_school_email_error(self.request)]
        )

    def test_non_email_rejected(self):
        bad_data = {'email': 'notanemail'}
        form = SendVerificationEmailForm(bad_data, view=MockView(self))
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['email'],
            ['Enter a valid email address.']
        )

    def test_SHI_accepted(self):
        good_data = {'email': 'tech@projectcallisto.org'}
        form = SendVerificationEmailForm(good_data, view=MockView(self))
        self.assertTrue(form.is_valid())

    @override_settings(DEBUG=True)
    def test_debug(self):
        good_data = {'email': 'hello@example.com'}
        form = SendVerificationEmailForm(good_data, view=MockView(self))
        self.assertTrue(form.is_valid())

    @override_settings(SITE_ID=4)
    def test_multiple_domains(self):
        good_data = {'email': 'tech@dons.usfca.edu'}
        form = SendVerificationEmailForm(good_data, view=MockView(self))
        self.assertTrue(form.is_valid())
        good_data = {'email': 'tech@usfca.edu'}
        form = SendVerificationEmailForm(good_data, view=MockView(self))
        self.assertTrue(form.is_valid())