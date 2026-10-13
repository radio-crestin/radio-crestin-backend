"""Clear song thumbnails that are a station's logo, not the song's cover.

Streaming pods reported them unfiltered, and a song is shared by every
station that plays it, so Aripi Spre Cer's logo was shown for Radio
Armonia's songs. Reports are filtered now (services/song_thumbnail.py);
this clears the thumbnails stored before. The rule is copied rather than
imported, so this migration does not change when the app code does.
"""

from urllib.parse import urlsplit

from django.db import migrations
from django.db.models import Q

# Narrows the rows down to those _is_station_logo has to look at.
_CANDIDATES = (
    Q(thumbnail_url__icontains='na.png')
    | Q(thumbnail_url__icontains='/station_logos/')
    | Q(thumbnail_url__icontains='no_cover_image.')
)
_UPDATE_BATCH = 1000


def _is_station_logo(url):
    parts = urlsplit(url.strip())
    host = (parts.hostname or '').casefold()
    path = parts.path.casefold()
    file_name = path.rsplit('/', 1)[-1]
    return (
        (host.endswith('aripisprecer.ro') and file_name == 'na.png')
        or (host == 'images.radio.co' and path.startswith('/station_logos/'))
        or file_name.startswith('no_cover_image.')
    )


def _clear(model):
    """Clears the station logo thumbnails of `model`'s rows; returns how
    many were cleared."""
    # A list, not .iterator(): server-side cursors fail behind PgBouncer.
    rows = model.objects.filter(_CANDIDATES).values_list('pk', 'thumbnail_url')
    pks = [pk for pk, url in rows if _is_station_logo(url)]
    for start in range(0, len(pks), _UPDATE_BATCH):
        model.objects.filter(
            pk__in=pks[start:start + _UPDATE_BATCH]).update(thumbnail_url=None)
    return len(pks)


def clear_station_logo_thumbnails(apps, schema_editor):
    songs = _clear(apps.get_model('radio_crestin', 'Songs'))
    now_playing = _clear(apps.get_model('radio_crestin', 'StationsNowPlaying'))
    print(f"Cleared station logo thumbnails of {songs} song(s) and "
          f"{now_playing} now playing row(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0052_timestamp_source_help_text'),
    ]

    operations = [
        # Not reversible in effect: the cleared URLs are not kept.
        migrations.RunPython(
            clear_station_logo_thumbnails, migrations.RunPython.noop),
    ]
