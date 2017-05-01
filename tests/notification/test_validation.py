from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from callisto.notification.models import EmailNotification


class EmailValidationTest(TestCase):

    def setUp(self):
        super(EmailValidationTest, self).setUp()
        for i in range(1, 10):
            site, _ = Site.objects.get_or_create(
                id=i,
            )
            site.domain = str(i)
            site.save()

    @override_settings()
    def test_validation_error_does_not_delete_email(self):
        del settings.SITE_ID
        for i in range(1, 10):
            email = EmailNotification.objects.create(
                name='example email',
                body='example email',
                subject='example email',
            )
            email.sites.add(i)
            email.full_clean()
        with self.assertRaises(ValidationError):
            invalid_email = EmailNotification.objects.get(
                name='example email',
                sites__id__in=[1],
            )
            invalid_email.sites.add(2)
            invalid_email.full_clean()
        self.assertTrue(invalid_email.pk)

    @override_settings()
    def test_duplicate_emails_not_allowed_on_same_site(self):
        del settings.SITE_ID
        site_id = 1
        with self.assertRaises(ValidationError):
            for i in range(10):
                email = EmailNotification.objects.create(
                    name='example email',
                    body='example email',
                    subject='example email',
                )
                email.sites.add(site_id)
                email.full_clean()
        self.assertEqual(EmailNotification.objects.on_site(site_id).count(), 1)

    @override_settings()
    def test_cannot_add_site_which_would_create_duplicate(self):
        del settings.SITE_ID
        for i in range(1, 10):
            email = EmailNotification.objects.create(
                name='example email',
                body='example email',
                subject='example email',
            )
            email.sites.add(i)
            email.full_clean()
        with self.assertRaises(ValidationError):
            email = EmailNotification.objects.get(
                name='example email',
                sites__id__in=[1],
            )
            email.sites.add(2)
            email.full_clean()
        self.assertEqual(EmailNotification.objects.on_site(2).count(), 1)
