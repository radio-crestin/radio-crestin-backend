from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import posthog
from superapp.apps.posthog_error_tracking.utils import track_event
from superapp.apps.posthog_error_tracking.error_handlers import track_error
from os import environ

User = get_user_model()


class Command(BaseCommand):
    help = 'Test PostHog error tracking integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-events',
            action='store_true',
            help='Test custom event tracking',
        )
        parser.add_argument(
            '--test-errors',
            action='store_true',
            help='Test error tracking',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Test all PostHog tracking features',
        )

    def handle(self, *args, **options):
        # Check if PostHog is configured
        if not environ.get('POSTHOG_API_KEY'):
            self.stdout.write(
                self.style.ERROR(
                    'PostHog is not configured. Please set POSTHOG_API_KEY in your environment.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS('PostHog Configuration:')
        )
        self.stdout.write(f'API Key: {environ.get("POSTHOG_API_KEY")[:10]}...')
        self.stdout.write(f'Host: {environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")}')
        
        if options['test_all'] or options['test_events']:
            self.test_event_tracking()
        
        if options['test_all'] or options['test_errors']:
            self.test_error_tracking()
        
        if not any([options['test_events'], options['test_errors'], options['test_all']]):
            self.stdout.write(
                self.style.WARNING(
                    'No test specified. Use --test-events, --test-errors, or --test-all'
                )
            )

    def test_event_tracking(self):
        self.stdout.write(
            self.style.HTTP_INFO('\n=== Testing Event Tracking ===')
        )
        
        # Test anonymous event tracking
        self.stdout.write('Testing anonymous event tracking...')
        track_event('anonymous', 'test_command_execution', {
            'test_type': 'management_command',
            'event_source': 'django_admin'
        })
        self.stdout.write(self.style.SUCCESS('✓ Anonymous event sent'))
        
        # Test user event tracking (if users exist)
        try:
            user = User.objects.first()
            if user:
                self.stdout.write(f'Testing user event tracking for user: {user.id}...')
                track_event(str(user.id), 'test_user_event', {
                    'test_type': 'management_command',
                    'user_email': getattr(user, 'email', ''),
                    'user_staff': getattr(user, 'is_staff', False)
                })
                self.stdout.write(self.style.SUCCESS('✓ User event sent'))
            else:
                self.stdout.write(self.style.WARNING('No users found for user event testing'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'User event test failed: {e}'))

    def test_error_tracking(self):
        self.stdout.write(
            self.style.HTTP_INFO('\n=== Testing Error Tracking ===')
        )
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/test-error-tracking/')
        request.user = User.objects.first() if User.objects.exists() else None
        
        # Test different error types
        self.stdout.write('Testing 404 error tracking...')
        track_error(
            request,
            error_type='Http404',
            error_message='Test 404 error from management command',
            status_code=404
        )
        self.stdout.write(self.style.SUCCESS('✓ 404 error tracked'))
        
        self.stdout.write('Testing 500 error tracking...')
        try:
            # Create a test exception
            raise ValueError("Test exception for PostHog tracking")
        except ValueError as e:
            track_error(
                request,
                error_type='ValueError',
                error_message=str(e),
                status_code=500,
                exception=e
            )
            self.stdout.write(self.style.SUCCESS('✓ 500 error tracked'))
        
        self.stdout.write('Testing 403 error tracking...')
        track_error(
            request,
            error_type='PermissionDenied',
            error_message='Test permission denied error',
            status_code=403
        )
        self.stdout.write(self.style.SUCCESS('✓ 403 error tracked'))
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ All tests completed successfully!')
        )
        self.stdout.write(
            self.style.HTTP_INFO(
                f'Check your PostHog dashboard at {environ.get("POSTHOG_HOST", "https://eu.i.posthog.com")} for the tracked events and errors.'
            )
        )