# Generated by Django 5.1.11 on 2025-07-21 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0007_alter_songs_unique_together_alter_songs_artist_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stationsmetadatafetch',
            name='order',
        ),
        migrations.AddField(
            model_name='stationsmetadatafetch',
            name='artist_regex',
            field=models.TextField(blank=True, help_text='Regex pattern to extract artist (optional)', null=True, verbose_name='Artist Regex'),
        ),
        migrations.AddField(
            model_name='stationsmetadatafetch',
            name='priority',
            field=models.IntegerField(default=1, help_text='Higher number = higher priority', verbose_name='Priority'),
        ),
        migrations.AddField(
            model_name='stationsmetadatafetch',
            name='split_character',
            field=models.CharField(default=' - ', help_text='Character(s) used to split artist and title', max_length=10, verbose_name='Split Character'),
        ),
        migrations.AddField(
            model_name='stationsmetadatafetch',
            name='station_name_regex',
            field=models.TextField(blank=True, help_text='Regex pattern to remove station name from title (optional)', null=True, verbose_name='Station Name Regex'),
        ),
        migrations.AddField(
            model_name='stationsmetadatafetch',
            name='title_regex',
            field=models.TextField(blank=True, help_text='Regex pattern to extract title (optional)', null=True, verbose_name='Title Regex'),
        ),
    ]
