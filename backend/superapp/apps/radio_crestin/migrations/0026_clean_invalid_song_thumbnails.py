# Generated manually to clean invalid aripisprecer.ro thumbnails

from django.db import migrations
from django.db.models import Q
from django.conf import settings
import hashlib
import requests


def get_image_hash(image_url: str, timeout: int = 5):
    """
    Fetch an image from URL and return its MD5 hash.

    Args:
        image_url: URL of the image to fetch
        timeout: Request timeout in seconds

    Returns:
        MD5 hash of the image content, or None if fetch fails
    """
    try:
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()
        return hashlib.md5(response.content).hexdigest()
    except Exception as e:
        print(f"Failed to fetch image from {image_url}: {e}")
        return None


def get_reference_colinde_thumbnail_hash():
    """
    Get the hash of the reference colinde thumbnail image.

    Returns:
        MD5 hash of the reference image, or None if file doesn't exist
    """
    try:
        reference_path = settings.BASE_DIR / 'assets' / 'asc_colinde_thumbnail.jpg'
        if reference_path.exists():
            with open(reference_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"Failed to read reference image: {e}")

    return None


def clean_invalid_thumbnails(apps, schema_editor):
    """
    Clean up invalid thumbnail URLs from aripisprecer.ro:
    1. Set to None if contains 'na.png' and 'aripisprecer.ro'
    2. Set to None if image hash matches the reference colinde thumbnail
    """
    Songs = apps.get_model('radio_crestin', 'Songs')

    # Find songs with na.png from aripisprecer.ro
    songs_with_na_png = Songs.objects.filter(
        Q(thumbnail_url__icontains='aripisprecer.ro') &
        Q(thumbnail_url__icontains='na.png')
    )
    na_png_count = songs_with_na_png.count()
    songs_with_na_png.update(thumbnail_url=None)

    print(f"Cleaned {na_png_count} songs with na.png thumbnails")

    # Get reference image hash
    reference_hash = get_reference_colinde_thumbnail_hash()

    if reference_hash:
        # Find songs with aripisprecer.ro thumbnails (excluding already cleaned na.png)
        songs_with_aripisprecer = Songs.objects.filter(
            thumbnail_url__icontains='aripisprecer.ro'
        ).exclude(thumbnail_url__isnull=True)

        colinde_count = 0
        for song in songs_with_aripisprecer:
            if song.thumbnail_url:
                image_hash = get_image_hash(song.thumbnail_url)
                if image_hash and image_hash == reference_hash:
                    song.thumbnail_url = None
                    song.save(update_fields=['thumbnail_url'])
                    colinde_count += 1

        print(f"Cleaned {colinde_count} songs with matching colinde thumbnail hash")
    else:
        print("Warning: Could not load reference colinde thumbnail for hash comparison")

    print(f"Total cleaned: {na_png_count + (colinde_count if reference_hash else 0)} songs")


def reverse_func(apps, schema_editor):
    # We can't reverse this operation as we don't store the old URLs
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('radio_crestin', '0025_alter_appusers_password_non_null'),
    ]

    operations = [
        migrations.RunPython(clean_invalid_thumbnails, reverse_func),
    ]
