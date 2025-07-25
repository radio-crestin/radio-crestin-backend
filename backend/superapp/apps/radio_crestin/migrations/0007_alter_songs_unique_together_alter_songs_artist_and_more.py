# Generated by Django 5.1.11 on 2025-07-21 07:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0006_appusers_alter_listeningevents_user_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='songs',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='songs',
            name='artist',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='radio_crestin.artists', verbose_name='Artist'),
        ),
        migrations.AddConstraint(
            model_name='songs',
            constraint=models.UniqueConstraint(condition=models.Q(('artist__isnull', False)), fields=('name', 'artist'), name='unique_song_artist'),
        ),
        migrations.AddConstraint(
            model_name='songs',
            constraint=models.UniqueConstraint(condition=models.Q(('artist__isnull', True)), fields=('name',), name='unique_song_no_artist'),
        ),
    ]
