# Generated by Django 5.1.5 on 2025-02-17 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0011_product_currency_product_location_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='bid_end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='buy_now_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='closed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='duration',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='starting_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
