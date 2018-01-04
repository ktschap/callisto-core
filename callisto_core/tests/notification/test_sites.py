from unittest import skip

from mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase

from callisto_core.notification.models import EmailNotification
from callisto_core.tests.test_base import (
    ReportFlowHelper as ReportFlowTestCase,
)
from callisto_core.utils.sites import TempSiteID

User = get_user_model()


class SiteIDTest(ReportFlowTestCase):

    def setUp(self):
        super().setUp()
        self.second_site = Site.objects.create(domain='generic_second_site')

    def test_on_site_respects_SITE_ID_setting(self):
        site_1 = Site.objects.get(id=1)
        site_2 = Site.objects.create()
        site_1_emails = 3
        site_2_emails = site_1_emails + 1

        with TempSiteID(site_1.id):
            site_1_email_count = EmailNotification.objects.on_site().count()
        with TempSiteID(site_2.id):
            site_2_email_count = EmailNotification.objects.on_site().count()

        index = 0
        for i in range(site_1_emails):
            notification = EmailNotification.objects.create(name=index)
            notification.sites.add(site_1)
            index += 1
        for i in range(site_2_emails):
            notification = EmailNotification.objects.create(name=index)
            notification.sites.add(site_2)
            index += 1

        with TempSiteID(site_1.id):
            self.assertEqual(
                EmailNotification.objects.on_site().count(),
                site_1_email_count + site_1_emails,
            )
        with TempSiteID(site_2.id):
            self.assertEqual(
                EmailNotification.objects.on_site().count(),
                site_2_email_count + site_2_emails,
            )

    def test_multiple_added_sites_are_reflected_by_on_site(self):
        site_2 = Site.objects.create()
        notification = EmailNotification.objects.create()
        notification.sites.add(1)
        notification.sites.add(site_2)

        with TempSiteID(1):
            self.assertIn(notification, EmailNotification.objects.on_site())

        with TempSiteID(site_2.id):
            self.assertIn(notification, EmailNotification.objects.on_site())


class SiteRequestTest(TestCase):

    @skip('temporariy disabled')
    def test_can_request_pages_without_site_id_set(self):
        self.client_post_report_creation()
        response = self.client_post_reporting()
        self.assertNotEqual(response.status_code, 404)

    @skip('temporariy disabled')
    @patch('...notification.managers.EmailNotificationQuerySet.on_site')
    def test_site_passed_to_email_notification_manager(self, mock_on_site):
        self.client_post_report_creation()
        self.client_post_reporting()
        mock_on_site.assert_called_with(self.site.id)
