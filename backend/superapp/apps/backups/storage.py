from storages.backends.s3boto3 import S3Boto3Storage

class PrivateBackupStorage(S3Boto3Storage):
    default_acl = 'private'
    file_overwrite = False
