# Generated by Django 5.1.5 on 2025-02-15 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0007_rename_bidder_bid_buyer_remove_bid_bid_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='is_payed',
            field=models.BooleanField(default=False),
        ),
    ]
