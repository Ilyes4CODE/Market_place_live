# Generated by Django 5.1.5 on 2025-02-06 22:51

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0006_bid_winner'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bid',
            old_name='bidder',
            new_name='buyer',
        ),
        migrations.RemoveField(
            model_name='bid',
            name='bid_date',
        ),
        migrations.RemoveField(
            model_name='bid',
            name='winner',
        ),
        migrations.AddField(
            model_name='bid',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bid',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending', max_length=10),
        ),
        migrations.AlterField(
            model_name='bid',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Product.product'),
        ),
    ]
