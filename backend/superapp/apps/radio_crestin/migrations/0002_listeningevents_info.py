# Generated by Django 5.1.11 on 2025-07-21 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='listeningevents',
            name='info',
            field=models.JSONField(blank=True, null=True, verbose_name='Info'),
        ),
    ]
