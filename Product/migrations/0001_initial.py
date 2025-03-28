# Generated by Django 5.1.5 on 2025-01-25 22:48

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('Auth', '0003_marketuser_profile_picture'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('upload_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('condition', models.CharField(choices=[('new', 'New'), ('used', 'Used')], default='new', max_length=10)),
                ('is_approved', models.BooleanField(default=False)),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='Auth.marketuser')),
            ],
        ),
        migrations.CreateModel(
            name='Listing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchase_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='Auth.marketuser')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='listings', to='Product.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProductPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo', models.ImageField(upload_to='product_photos/')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='Product.product')),
            ],
        ),
    ]
