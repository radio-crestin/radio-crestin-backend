# Indexes for the admin list pages' default ordering, so they read only the newest
# rows instead of sorting the whole table. Built CONCURRENTLY: no write lock in production.
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('radio_crestin', '0072_announcement_stat_buckets'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='reviews',
            index=models.Index(fields=['created_at'], name='reviews_created_at_idx'),
        ),
        AddIndexConcurrently(
            model_name='listeningsessions',
            index=models.Index(fields=['last_activity'], name='listening_last_activity_idx'),
        ),
    ]
