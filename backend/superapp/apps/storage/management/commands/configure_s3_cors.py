"""
Django management command to configure CORS settings for S3 buckets.
"""
import json
from os import environ
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
import boto3
from botocore.exceptions import BotoCoreError, ClientError


class Command(BaseCommand):
    help = _('Configure CORS settings for public and static file S3 buckets')

    def add_arguments(self, parser):
        parser.add_argument(
            '--origins',
            type=str,
            nargs='+',
            default=['*'],
            help=_('Allowed origins (default: * for all origins)')
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=_('Show what would be done without making changes')
        )
        parser.add_argument(
            '--view-current',
            action='store_true',
            help=_('View current CORS configuration')
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        try:
            # Get configuration
            public_config = self._get_public_storage_config()
            static_config = self._get_static_storage_config()

            if options['view_current']:
                self._view_cors_config(public_config, static_config)
                return

            # Configure CORS for both buckets
            self._configure_bucket_cors(
                public_config, 
                'public', 
                options['origins'], 
                options['dry_run']
            )
            
            self._configure_bucket_cors(
                static_config, 
                'static', 
                options['origins'], 
                options['dry_run']
            )

        except Exception as e:
            raise CommandError(f"Failed to configure CORS: {e}")

    def _get_public_storage_config(self):
        """Get public storage S3 configuration."""
        return {
            'access_key': environ.get("AWS_PUBLIC_ACCESS_KEY_ID"),
            'secret_key': environ.get("AWS_PUBLIC_SECRET_ACCESS_KEY"),
            'bucket_name': environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME"),
            'endpoint_url': environ.get("AWS_PUBLIC_ENDPOINT_URL"),
            'region_name': environ.get("AWS_PUBLIC_S3_REGION_NAME", "fsn1"),
        }

    def _get_static_storage_config(self):
        """Get static storage S3 configuration."""
        return {
            'access_key': environ.get("AWS_STATIC_ACCESS_KEY_ID", environ.get("AWS_PUBLIC_ACCESS_KEY_ID")),
            'secret_key': environ.get("AWS_STATIC_SECRET_ACCESS_KEY", environ.get("AWS_PUBLIC_SECRET_ACCESS_KEY")),
            'bucket_name': environ.get("AWS_STATIC_STORAGE_BUCKET_NAME", environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME")),
            'endpoint_url': environ.get("AWS_STATIC_ENDPOINT_URL", environ.get("AWS_PUBLIC_ENDPOINT_URL")),
            'region_name': environ.get("AWS_STATIC_S3_REGION_NAME", environ.get("AWS_PUBLIC_S3_REGION_NAME", "fsn1")),
        }

    def _create_s3_client(self, config):
        """Create S3 client with the given configuration."""
        if not all([config['access_key'], config['secret_key'], config['bucket_name'], config['endpoint_url']]):
            raise CommandError("Missing required S3 configuration. Please check your environment variables.")

        return boto3.client(
            's3',
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            endpoint_url=config['endpoint_url'],
            region_name=config['region_name'],
        )

    def _create_cors_configuration(self, origins):
        """Create CORS configuration."""
        return {
            'CORSRules': [
                {
                    'AllowedOrigins': origins,
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'HEAD'],
                    'MaxAgeSeconds': 3600,
                }
            ]
        }

    def _configure_bucket_cors(self, config, bucket_type, origins, dry_run=False):
        """Configure CORS for a specific bucket."""
        bucket_name = config['bucket_name']
        
        if not bucket_name:
            self.stdout.write(
                self.style.WARNING(f"No bucket configured for {bucket_type} storage - skipping")
            )
            return

        self.stdout.write(f"Configuring CORS for {bucket_type} bucket: {bucket_name}")

        try:
            s3_client = self._create_s3_client(config)
            cors_config = self._create_cors_configuration(origins)

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"DRY RUN - Would apply CORS configuration to {bucket_name}:")
                )
                self.stdout.write(json.dumps(cors_config, indent=2))
                return

            # Apply CORS configuration
            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_config
            )

            self.stdout.write(
                self.style.SUCCESS(f"Successfully configured CORS for {bucket_name}")
            )

            # Display applied configuration
            self.stdout.write("Applied CORS configuration:")
            self.stdout.write(json.dumps(cors_config, indent=2))

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise CommandError(f"AWS S3 error for {bucket_name}: {error_code} - {error_message}")
        except BotoCoreError as e:
            raise CommandError(f"Boto3 error for {bucket_name}: {e}")

    def _view_cors_config(self, public_config, static_config):
        """View current CORS configuration for buckets."""
        self.stdout.write(self.style.SUCCESS("Current CORS configurations:"))
        
        self._view_bucket_cors(public_config, 'public')
        self._view_bucket_cors(static_config, 'static')

    def _view_bucket_cors(self, config, bucket_type):
        """View CORS configuration for a specific bucket."""
        bucket_name = config['bucket_name']
        
        if not bucket_name:
            self.stdout.write(f"\n{bucket_type.upper()} BUCKET: Not configured")
            return

        self.stdout.write(f"\n{bucket_type.upper()} BUCKET: {bucket_name}")

        try:
            s3_client = self._create_s3_client(config)
            
            # Get current CORS configuration
            response = s3_client.get_bucket_cors(Bucket=bucket_name)
            cors_config = response.get('CORSRules', [])
            
            if cors_config:
                self.stdout.write("CORS Rules:")
                for i, rule in enumerate(cors_config, 1):
                    self.stdout.write(f"  Rule {i}:")
                    self.stdout.write(f"    Allowed Origins: {rule.get('AllowedOrigins', [])}")
                    self.stdout.write(f"    Allowed Methods: {rule.get('AllowedMethods', [])}")
                    self.stdout.write(f"    Allowed Headers: {rule.get('AllowedHeaders', [])}")
                    if 'MaxAgeSeconds' in rule:
                        self.stdout.write(f"    Max Age: {rule['MaxAgeSeconds']} seconds")
            else:
                self.stdout.write("  No CORS rules configured")

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
                self.stdout.write("  No CORS configuration found")
            else:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                self.stdout.write(
                    self.style.ERROR(f"  Error: {error_code} - {error_message}")
                )
        except BotoCoreError as e:
            self.stdout.write(
                self.style.ERROR(f"  Boto3 error: {e}")
            )