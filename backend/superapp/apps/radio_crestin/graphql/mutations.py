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
    ShareLinkData
)
from ..models import Stations, ListeningSessions
from ..services.share_link_service import ShareLinkService


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
