# Generated by Django 5.1.5 on 2025-02-15 12:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0008_listing_is_payed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationbid',
            name='bid',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='Product.bid'),
        ),
    ]
