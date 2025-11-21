"""
Storage configuration for different storage types.
Provides centralized configuration for private, public, and static file storage.
"""
from os import environ
from django.conf import settings
from storages.backends.s3 import S3Storage


class PrivateS3Storage(S3Storage):
    """Custom S3 storage for private files."""
    
    @property
    def access_key(self):
        return environ.get("AWS_PRIVATE_ACCESS_KEY_ID")
    
    @property
    def secret_key(self):
        return environ.get("AWS_PRIVATE_SECRET_ACCESS_KEY")
    
    @property
    def bucket_name(self):
        return environ.get("AWS_PRIVATE_STORAGE_BUCKET_NAME")
    
    @property
    def endpoint_url(self):
        return environ.get("AWS_PRIVATE_ENDPOINT_URL")
    
    @property
    def region_name(self):
        return environ.get("AWS_PRIVATE_S3_REGION_NAME", "fsn1")
    
    @property
    def signature_version(self):
        return environ.get("AWS_PRIVATE_S3_SIGNATURE_VERSION", "s3v4")
    
    @property
    def addressing_style(self):
        return "path"
    
    @property
    def use_ssl(self):
        return environ.get("AWS_PRIVATE_USE_SSL", "True").lower() == "true"
    
    @property
    def custom_domain(self):
        return None
    
    @property
    def location(self):
        return environ.get("AWS_PRIVATE_LOCATION", "private/")
    
    @property
    def querystring_auth(self):
        return True
    
    @property
    def default_acl(self):
        return "private"


class PublicS3Storage(S3Storage):
    """Custom S3 storage for public files."""
    
    @property
    def access_key(self):
        return environ.get("AWS_PUBLIC_ACCESS_KEY_ID")
    
    @property
    def secret_key(self):
        return environ.get("AWS_PUBLIC_SECRET_ACCESS_KEY")
    
    @property
    def bucket_name(self):
        return environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME")
    
    @property
    def endpoint_url(self):
        return environ.get("AWS_PUBLIC_ENDPOINT_URL")
    
    @property
    def region_name(self):
        return environ.get("AWS_PUBLIC_S3_REGION_NAME", "fsn1")
    
    @property
    def signature_version(self):
        return environ.get("AWS_PUBLIC_S3_SIGNATURE_VERSION", "s3v4")
    
    @property
    def addressing_style(self):
        return "path"
    
    @property
    def use_ssl(self):
        return environ.get("AWS_PUBLIC_USE_SSL", "True").lower() == "true"
    
    @property
    def custom_domain(self):
        return None
    
    @property
    def location(self):
        return environ.get("AWS_PUBLIC_LOCATION", "public/")
    
    @property
    def querystring_auth(self):
        return False
    
    @property
    def default_acl(self):
        return "public-read"


class StaticS3Storage(S3Storage):
    """Custom S3 storage for static files."""
    
    @property
    def access_key(self):
        return environ.get("AWS_STATIC_ACCESS_KEY_ID", environ.get("AWS_PUBLIC_ACCESS_KEY_ID"))
    
    @property
    def secret_key(self):
        return environ.get("AWS_STATIC_SECRET_ACCESS_KEY", environ.get("AWS_PUBLIC_SECRET_ACCESS_KEY"))
    
    @property
    def bucket_name(self):
        return environ.get("AWS_STATIC_STORAGE_BUCKET_NAME", environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME"))
    
    @property
    def endpoint_url(self):
        return environ.get("AWS_STATIC_ENDPOINT_URL", environ.get("AWS_PUBLIC_ENDPOINT_URL"))
    
    @property
    def region_name(self):
        return environ.get("AWS_STATIC_S3_REGION_NAME", environ.get("AWS_PUBLIC_S3_REGION_NAME", "fsn1"))
    
    @property
    def signature_version(self):
        return environ.get("AWS_STATIC_S3_SIGNATURE_VERSION", environ.get("AWS_PUBLIC_S3_SIGNATURE_VERSION", "s3v4"))
    
    @property
    def addressing_style(self):
        return "path"
    
    @property
    def use_ssl(self):
        return environ.get("AWS_STATIC_USE_SSL", environ.get("AWS_PUBLIC_USE_SSL", "True")).lower() == "true"
    
    @property
    def custom_domain(self):
        return None
    
    @property
    def location(self):
        return environ.get("AWS_STATIC_LOCATION", "static/")
    
    @property
    def querystring_auth(self):
        return False
    
    @property
    def default_acl(self):
        return "public-read"


class StorageConfig:
    """
    Centralized storage configuration handling private, public, and static file storage.
    """

    @staticmethod
    def get_private_storage_config():
        """Get private storage configuration."""
        if environ.get("AWS_PRIVATE_ACCESS_KEY_ID"):
            return {
                "BACKEND": "superapp.apps.storage.config.PrivateS3Storage",
                "OPTIONS": {},
            }
        else:
            return {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
                "OPTIONS": {},
            }

    @staticmethod
    def get_public_storage_config():
        """Get public storage configuration."""
        if environ.get("AWS_PUBLIC_ACCESS_KEY_ID"):
            return {
                "BACKEND": "superapp.apps.storage.config.PublicS3Storage",
                "OPTIONS": {},
            }
        else:
            return {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
                "OPTIONS": {},
            }

    @staticmethod
    def get_static_storage_config():
        """Get static files storage configuration."""
        debug = getattr(settings, 'DEBUG', False)

        # Check if static or public storage is configured and not in debug mode
        if (environ.get("AWS_STATIC_ACCESS_KEY_ID") or environ.get("AWS_PUBLIC_ACCESS_KEY_ID")) and not debug:
            return {
                "BACKEND": "superapp.apps.storage.config.StaticS3Storage",
                "OPTIONS": {},
            }
        else:
            return {
                "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
                "OPTIONS": {},
            }

    @staticmethod
    def get_storage_settings():
        """Get complete storage settings configuration."""
        return {
            'default': StorageConfig.get_private_storage_config(),
            'private': StorageConfig.get_private_storage_config(),
            'public': StorageConfig.get_public_storage_config(),
            'staticfiles': StorageConfig.get_static_storage_config(),
        }
    
    @staticmethod
    def get_static_url():
        """Get the static URL based on storage configuration."""
        debug = getattr(settings, 'DEBUG', False)
        
        # If using S3 storage (not in debug mode and S3 configured)
        if (environ.get("AWS_STATIC_ACCESS_KEY_ID") or environ.get("AWS_PUBLIC_ACCESS_KEY_ID")) and not debug:
            endpoint_url = environ.get("AWS_STATIC_ENDPOINT_URL", environ.get("AWS_PUBLIC_ENDPOINT_URL"))
            bucket_name = environ.get("AWS_STATIC_STORAGE_BUCKET_NAME", environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME"))
            location = environ.get("AWS_STATIC_LOCATION", "static/")
            
            if endpoint_url and bucket_name:
                # Remove trailing slash from endpoint_url and location
                endpoint_url = endpoint_url.rstrip('/')
                location = location.rstrip('/')
                
                return f"{endpoint_url}/{bucket_name}/{location}/"
        
        # Default static URL
        return "/static/"
