# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-26 12:18
from __future__ import unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0005_bulkaccount_verbose_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]