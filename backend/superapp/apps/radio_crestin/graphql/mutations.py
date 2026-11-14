import os
import typing

import strawberry
from typing import List, Optional

import strawberry_django
from datetime import datetime
import logging

from strawberry import BasePermission
from strawberry_django.auth.utils import get_current_user

from .types import (
    ListeningEventInput,
    SubmitListeningEventsResponse,
    TriggerMetadataFetchResponse,
    CreateShareLinkInput,
    CreateShareLinkResponse,
    GetShareLinkResponse,
    ShareLinkData,
    SubmitReviewInput,
    SubmitReviewResponse,
    DeleteReviewInput,
    DeleteReviewResponse,
    ReviewType,
    AnalyticsEventInput,
    AnalyticsEventResponse,
    ReportStationMetadataInput,
    ReportStationMetadataResponse,
)
from ..models import Stations, ListeningSessions, AppUsers
from ..services.share_link_service import ShareLinkService
from ..services.review_service import ReviewService
from ..services.listening_events import record_listening_events
from ..utils.streaming_pod_auth import is_streaming_pod
from ..utils.rate_limits import over_limit
from ..utils.client_request import client_ip


# Public writes, per client IP. Generous: many phones share one carrier
# (CGNAT) address, and a person leaves a few reviews at most.
REVIEW_RATE_PER_IP = '30/h'
SHARE_LINK_RATE_PER_IP = '120/h'
RATE_LIMITED_MESSAGE = "Too many requests; try again later."
MAX_REVIEW_MESSAGE_LENGTH = 2000
MAX_USER_IDENTIFIER_LENGTH = 255
MAX_ANONYMOUS_ID_LENGTH = 512


class IsSuperuser(BasePermission):
    message = "User is not a superuser"

    def has_permission(
            self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        user = get_current_user(info)
        if not user or not user.is_authenticated or not getattr(user, "is_superuser", False):
            return False
        return True


class IsStreamingPod(BasePermission):
    message = "Invalid streaming pod API key"

    def has_permission(
            self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        return is_streaming_pod(info.context.request)


@strawberry.type
class Mutation:
    """
    Placeholder mutations for radio_crestin app.
    Add specific mutations as needed for station management.
    """

    @strawberry.field
    def health_check(self) -> str:
        """Health check mutation for radio_crestin GraphQL"""
        return "Radio Crestin GraphQL mutations are healthy"

    @strawberry_django.mutation(handle_django_errors=True, permission_classes=[IsStreamingPod])
    def submit_listening_events(self, events: List[ListeningEventInput]) -> SubmitListeningEventsResponse:
        """Submit batch of listening events from HLS streaming logs"""
        try:
            processed_count = record_listening_events(events)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error in submit_listening_events: {e}")
            return SubmitListeningEventsResponse(
                success=False,
                message="Error processing events",
                processed_count=0
            )
        return SubmitListeningEventsResponse(
            success=True,
            message=f"Successfully processed {processed_count}/{len(events)} events",
            processed_count=processed_count
        )

    @strawberry_django.mutation(handle_django_errors=True, permission_classes=[IsSuperuser])
    def trigger_metadata_fetch(self, station_id: int) -> TriggerMetadataFetchResponse:
        """Schedule a metadata fetch task for a specific station"""
        from superapp.apps.radio_crestin_scraping.tasks.scrape_station_metadata import scrape_station_metadata

        logger = logging.getLogger(__name__)

        try:
            station = Stations.objects.only('title').get(id=station_id)
            scrape_station_metadata.delay(station_id)
            logger.info(f"Metadata fetch task scheduled for station {station.title} (ID: {station_id})")

            return TriggerMetadataFetchResponse(
                success=True,
                message=f"Metadata fetch task scheduled for station {station.title}"
            )

        except Stations.DoesNotExist:
            logger.warning(f"Station not found: {station_id}")
            return TriggerMetadataFetchResponse(
                success=False,
                message=f"Station with ID {station_id} not found"
            )

        except Exception as e:
            logger.error(f"Error scheduling metadata fetch for station {station_id}: {e}")
            return TriggerMetadataFetchResponse(
                success=False,
                message="Error scheduling metadata fetch"
            )

    @strawberry_django.mutation(handle_django_errors=True)
    def get_share_link(self, info: strawberry.Info, anonymous_id: str) -> GetShareLinkResponse:
        """Get or create the unique share link for a user"""
        logger = logging.getLogger(__name__)

        if not anonymous_id or len(anonymous_id) > MAX_ANONYMOUS_ID_LENGTH:
            return GetShareLinkResponse(success=False, message="Invalid anonymous_id", anonymous_id=anonymous_id[:64])
        request = info.context.request
        if over_limit(request, 'share-link-ip', Mutation._get_client_ip(request), SHARE_LINK_RATE_PER_IP):
            return GetShareLinkResponse(success=False, message=RATE_LIMITED_MESSAGE, anonymous_id=anonymous_id)

        try:
            # Get share link info from service (will create user and link if needed)
            result = ShareLinkService.get_share_link_info(anonymous_id)

            # Convert to GraphQL type
            link_info = result['share_link']

            # Create share message template
            share_message = "Te invit să asculți acest post de Radio Creștin: {url}"

            # Create station-specific share message template for client-side rendering
            share_station_message = "Te invit să asculți {station_name}: {url}"

            # Create share section title and message with visitor count
            share_section_title = "Ajută la răspândirea Evangheliei"
            share_section_message = (
                "Trimite această aplicație prietenilor tăi pentru a-L cunoaște pe Mântuitorul și Salvatorul lumii."
            )

            share_link_data = ShareLinkData(
                share_id=link_info['share_id'],
                url=link_info['root_url'],
                share_message=share_message,
                visit_count=link_info['visit_count'],
                created_at=link_info['created_at'],
                is_active=link_info['is_active'],
                share_section_title=share_section_title,
                share_section_message=share_section_message,
                share_station_message=share_station_message
            )

            return GetShareLinkResponse(
                success=True,
                message="Share link retrieved successfully",
                anonymous_id=anonymous_id,
                share_link=share_link_data
            )

        except Exception as e:
            logger.error(f"Error getting share link: {e}")
            return GetShareLinkResponse(
                success=False,
                message="Error getting share link",
                anonymous_id=anonymous_id
            )

    @strawberry_django.mutation(handle_django_errors=True)
    def submit_review(self, info: strawberry.Info, input: SubmitReviewInput) -> SubmitReviewResponse:
        """
        Submit or update a review for a radio station.

        Reviews are unique per IP address and station. If the same IP submits
        another review for the same station, the existing review is updated.
        """
        logger = logging.getLogger(__name__)

        try:
            # Extract IP address from request
            request = info.context.request
            ip_address = Mutation._get_client_ip(request)

            if not ip_address:
                return SubmitReviewResponse(
                    success=False,
                    message="Could not determine client IP address",
                    created=False
                )
            if over_limit(request, 'review-ip', ip_address, REVIEW_RATE_PER_IP):
                return SubmitReviewResponse(success=False, message=RATE_LIMITED_MESSAGE, created=False)
            if input.message and len(input.message) > MAX_REVIEW_MESSAGE_LENGTH:
                return SubmitReviewResponse(
                    success=False,
                    message=f"The message is longer than {MAX_REVIEW_MESSAGE_LENGTH} characters",
                    created=False,
                )
            if input.user_identifier and len(input.user_identifier) > MAX_USER_IDENTIFIER_LENGTH:
                return SubmitReviewResponse(success=False, message="Invalid user_identifier", created=False)

            # Resolve station_id from station_slug if needed
            station_id = input.station_id
            if not station_id and input.station_slug:
                station = Stations.objects.filter(slug=input.station_slug, disabled=False).first()
                if not station:
                    return SubmitReviewResponse(
                        success=False,
                        message=f"Station '{input.station_slug}' not found",
                        created=False,
                    )
                station_id = station.id

            if not station_id:
                return SubmitReviewResponse(
                    success=False,
                    message="Either station_id or station_slug is required",
                    created=False,
                )

            # Use the ReviewService to upsert the review
            result = ReviewService.upsert(
                station_id=station_id,
                ip_address=ip_address,
                stars=input.stars,
                message=input.message,
                user_identifier=input.user_identifier,
                song_id=input.song_id
            )

            review_data = result['review']
            review_type = ReviewType(
                id=review_data['id'],
                station_id=review_data['station_id'],
                song_id=review_data['song_id'],
                stars=review_data['stars'],
                message=review_data['message'],
                user_identifier=review_data['user_identifier'],
                created_at=review_data['created_at'],
                updated_at=review_data['updated_at'],
                verified=review_data['verified']
            )

            action = "created" if result['created'] else "updated"
            return SubmitReviewResponse(
                success=True,
                message=f"Review {action} successfully",
                review=review_type,
                created=result['created']
            )

        except ValueError as e:
            logger.warning(f"Validation error in submit_review: {e}")
            return SubmitReviewResponse(
                success=False,
                message=str(e),
                created=False
            )
        except Exception as e:
            logger.error(f"Error submitting review: {e}")
            return SubmitReviewResponse(
                success=False,
                message="Error submitting review",
                created=False
            )

    @strawberry_django.mutation(handle_django_errors=True)
    def delete_review(self, info: strawberry.Info, input: DeleteReviewInput) -> DeleteReviewResponse:
        """
        Delete a review for a radio station, optionally scoped to a specific song.
        The review is identified by the caller's IP address + station + optional song.
        """
        logger = logging.getLogger(__name__)

        try:
            request = info.context.request
            ip_address = Mutation._get_client_ip(request)

            if not ip_address:
                return DeleteReviewResponse(
                    success=False,
                    message="Could not determine client IP address"
                )
            if over_limit(request, 'review-ip', ip_address, REVIEW_RATE_PER_IP):
                return DeleteReviewResponse(success=False, message=RATE_LIMITED_MESSAGE)

            station_id = input.station_id
            if not station_id and input.station_slug:
                station = Stations.objects.filter(slug=input.station_slug, disabled=False).first()
                if not station:
                    return DeleteReviewResponse(
                        success=False,
                        message=f"Station '{input.station_slug}' not found"
                    )
                station_id = station.id

            if not station_id:
                return DeleteReviewResponse(
                    success=False,
                    message="Either station_id or station_slug is required"
                )

            deleted = ReviewService.delete(
                station_id=station_id,
                ip_address=ip_address,
                song_id=input.song_id
            )

            if deleted:
                return DeleteReviewResponse(
                    success=True,
                    message="Review deleted successfully"
                )
            else:
                return DeleteReviewResponse(
                    success=False,
                    message="Review not found"
                )

        except Exception as e:
            logger.error(f"Error deleting review: {e}")
            return DeleteReviewResponse(
                success=False,
                message="Error deleting review"
            )

    @strawberry.mutation
    def insert_analytics_events_one(self, object: AnalyticsEventInput) -> AnalyticsEventResponse:
        """
        Legacy Hasura-compatible mutation for analytics events.
        Accepts the request but does nothing — analytics are tracked via PostHog.
        """
        return AnalyticsEventResponse(id=0)

    @strawberry_django.mutation(handle_django_errors=True, permission_classes=[IsStreamingPod])
    def report_station_metadata(self, input: ReportStationMetadataInput) -> ReportStationMetadataResponse:
        """Report metadata from a streaming pod back to Django.
        Called by pods when they detect a song change via their configured scrapers."""
        logger = logging.getLogger(__name__)
        try:
            from ..services.pod_metadata_service import PodMetadataService
            result = PodMetadataService.report_metadata(input)
            return ReportStationMetadataResponse(
                success=True,
                message=f"Metadata reported for station {input.station_slug}",
                song_id=result.get('song_id'),
                thumbnail_url=result.get('thumbnail_url'),
                song_title=result.get('song_title'),
                song_artist=result.get('song_artist'),
                song_artist_id=result.get('song_artist_id'),
                song_thumbnail_url=result.get('song_thumbnail_url'),
                history_timestamp=result.get('history_timestamp'),
            )
        except Stations.DoesNotExist:
            return ReportStationMetadataResponse(
                success=False,
                message=f"Station '{input.station_slug}' not found",
            )
        except Exception as e:
            logger.error(f"Error reporting station metadata: {e}")
            return ReportStationMetadataResponse(
                success=False,
                message="Error reporting metadata",
            )

    @staticmethod
    def _get_client_ip(request) -> str:
        """The caller's IP (utils/client_request.client_ip: forwarded
        headers count only from trusted proxies)."""
        return client_ip(request)
