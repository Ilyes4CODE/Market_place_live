# Generated by Django 5.1.5 on 2025-01-28 15:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Auth', '0003_marketuser_profile_picture'),
        ('Chats', '0003_message_seen_alter_conversation_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_notifications', to='Auth.marketuser'),
        ),
    ]
