# Generated by Django 5.1.5 on 2025-01-27 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0002_category_product_sale_type_alter_product_price_bid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='sold',
            field=models.BooleanField(default=False),
        ),
    ]
