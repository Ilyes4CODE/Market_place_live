# Generated by Django 5.1.5 on 2025-01-28 15:30

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0004_notificationbid'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationbid',
            name='timestamp',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
    ]
