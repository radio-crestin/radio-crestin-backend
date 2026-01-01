from __future__ import annotations

import typing

import strawberry
from typing import List

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
    ReviewType
)
from ..models import Stations, ListeningSessions
from ..services.share_link_service import ShareLinkService
from ..services.review_service import ReviewService


class IsSuperuser(BasePermission):
    message = "User is not a superuser"

    # This method can also be async!
    def has_permission(
            self, source: typing.Any, info: strawberry.Info, **kwargs
    ) -> bool:
        user = get_current_user(info)
        if not user or not user.is_authenticated or not getattr(user, "is_superuser", False):
            return False
        return True


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

    @strawberry_django.mutation(handle_django_errors=True, permission_classes=[IsSuperuser])
    def submit_listening_events(self, events: List[ListeningEventInput]) -> SubmitListeningEventsResponse:
        """Submit batch of listening events from HLS streaming logs"""
        logger = logging.getLogger(__name__)
        processed_count = 0

        try:
            for event_input in events:
                logger.info("Processing event: %s", event_input)
                try:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(event_input.timestamp.replace('Z', '+00:00'))

                    # Find or get station by slug
                    try:
                        station = Stations.objects.get(slug=event_input.station_slug)
                    except Stations.DoesNotExist:
                        logger.warning(f"Station not found: {event_input.station_slug}")
                        continue

                    # For anonymous sessions, don't create AppUser records
                    # Anonymous sessions are tracked by session ID only
                    anonymous_user = None

                    # Get or create listening session and update activity
                    session, created = ListeningSessions.get_or_create_session(
                        user=anonymous_user,
                        station=station,
                        anonymous_session_id=event_input.anonymous_session_id,
                        ip_address=event_input.ip_address,
                        user_agent=event_input.user_agent
                    )

                    # Update session activity with new event data
                    is_playlist = event_input.event_type == 'playlist_request'
                    session.update_activity(
                        timestamp=timestamp,
                        bytes_sent=event_input.bytes_transferred,
                        is_playlist=is_playlist
                    )

                    processed_count += 1

                except Exception as event_error:
                    logger.error(f"Error processing individual event: {event_error}")
                    continue

            return SubmitListeningEventsResponse(
                success=True,
                message=f"Successfully processed {processed_count}/{len(events)} events",
                processed_count=processed_count
            )

        except Exception as e:
            logger.error(f"Error in submit_listening_events: {e}")
            return SubmitListeningEventsResponse(
                success=False,
                message=f"Error processing events: {str(e)}",
                processed_count=processed_count
            )

    @strawberry_django.mutation(handle_django_errors=True, permission_classes=[IsSuperuser])
    def trigger_metadata_fetch(self, station_id: int) -> TriggerMetadataFetchResponse:
        """Schedule a metadata fetch task for a specific station"""
        logger = logging.getLogger(__name__)

        try:
            # Validate that the station exists
            station = Stations.objects.get(id=station_id)

            # For now, we'll just return success indicating the task was scheduled
            # In a real implementation, this would trigger a background task
            # using Celery, Django-RQ, or similar task queue system
            logger.info(f"Metadata fetch task scheduled for station {station.name} (ID: {station_id})")

            return TriggerMetadataFetchResponse(
                success=True,
                message=f"Metadata fetch task scheduled for station {station.name}"
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
                message=f"Error scheduling metadata fetch: {str(e)}"
            )

    @strawberry_django.mutation(handle_django_errors=True)
    def get_share_link(self, anonymous_id: str) -> GetShareLinkResponse:
        """Get or create the unique share link for a user"""
        logger = logging.getLogger(__name__)

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
                message=f"Error getting share link: {str(e)}",
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

            # Use the ReviewService to upsert the review
            result = ReviewService.upsert(
                station_id=input.station_id,
                ip_address=ip_address,
                stars=input.stars,
                message=input.message,
                user_identifier=input.user_identifier
            )

            review_data = result['review']
            review_type = ReviewType(
                id=review_data['id'],
                station_id=review_data['station_id'],
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
                message=f"Error submitting review: {str(e)}",
                created=False
            )

    @staticmethod
    def _get_client_ip(request) -> str:
        """
        Extract client IP from request, handling various proxy configurations.

        Checks headers in order of priority:
        1. CF-Connecting-IP (Cloudflare)
        2. X-Real-IP (Nginx proxy_set_header X-Real-IP)
        3. X-Forwarded-For (Standard proxy header, takes first IP)
        4. REMOTE_ADDR (Direct connection fallback)
        """
        # Cloudflare
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip:
            return cf_connecting_ip.strip()

        # Nginx X-Real-IP (single IP set by proxy)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()

        # X-Forwarded-For (may contain chain of IPs: client, proxy1, proxy2)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain (original client)
            return x_forwarded_for.split(',')[0].strip()

        # Direct connection
        return request.META.get('REMOTE_ADDR', '')
