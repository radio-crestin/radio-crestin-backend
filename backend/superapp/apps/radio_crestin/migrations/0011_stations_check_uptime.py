# Generated by Django 5.1.11 on 2025-07-21 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0010_add_search_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='stations',
            name='check_uptime',
            field=models.BooleanField(default=True, verbose_name='Check Uptime'),
        ),
    ]
