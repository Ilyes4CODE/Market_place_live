# Generated by Django 5.1.5 on 2025-02-07 16:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Auth', '0003_marketuser_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketuser',
            name='is_banned',
            field=models.BooleanField(default=False),
        ),
    ]
