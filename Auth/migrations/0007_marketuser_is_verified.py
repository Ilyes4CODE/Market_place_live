# Generated by Django 5.1.5 on 2025-02-11 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Auth', '0006_remove_marketuser_auth_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketuser',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
