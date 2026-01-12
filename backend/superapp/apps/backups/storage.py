from superapp.apps.storage.config import PrivateS3Storage


class PrivateBackupStorage(PrivateS3Storage):
    """
    Custom S3 storage for backup files.
    Extends PrivateS3Storage with backup-specific settings.
    """
    file_overwrite = False

    @property
    def location(self):
        return "backups/"
