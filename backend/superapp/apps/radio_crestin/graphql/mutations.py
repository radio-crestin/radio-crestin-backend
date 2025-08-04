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
    GetShareLinksResponse,
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
    def create_share_link(self, input: CreateShareLinkInput) -> CreateShareLinkResponse:
        """Create a share link for a user with optional station"""
        logger = logging.getLogger(__name__)
        
        try:
            # Upsert user with provided information
            user = ShareLinkService.upsert_user(
                anonymous_id=input.user_id,
                first_name=input.first_name,
                last_name=input.last_name,
                email=input.email
            )
            
            # Get station if slug provided
            station = None
            if input.station_slug:
                try:
                    station = Stations.objects.get(slug=input.station_slug)
                except Stations.DoesNotExist:
                    return CreateShareLinkResponse(
                        success=False,
                        message=f"Station with slug '{input.station_slug}' not found"
                    )
            
            # Create or get share link
            share_link = ShareLinkService.upsert_share_link(
                user=user,
                station=station
            )
            
            # Prepare response data
            share_link_data = ShareLinkData(
                share_id=share_link.share_id,
                url=share_link.get_full_url(),
                station_slug=station.slug if station else None,
                station_title=station.title if station else None,
                visit_count=share_link.visit_count,
                created_at=share_link.created_at.isoformat(),
                is_active=share_link.is_active
            )
            
            return CreateShareLinkResponse(
                success=True,
                message="Share link created successfully",
                share_link=share_link_data
            )
            
        except Exception as e:
            logger.error(f"Error creating share link: {e}")
            return CreateShareLinkResponse(
                success=False,
                message=f"Error creating share link: {str(e)}"
            )
    
    @strawberry_django.mutation(handle_django_errors=True)
    def get_share_links(self, user_id: str) -> GetShareLinksResponse:
        """Get all share links for a user with visitor counts"""
        logger = logging.getLogger(__name__)
        
        try:
            # Get share link info from service
            result = ShareLinkService.get_share_link_info(user_id)
            
            if 'error' in result:
                return GetShareLinksResponse(
                    success=False,
                    message=result['error'],
                    user_id=user_id
                )
            
            # Convert to GraphQL types
            share_links_data = []
            for link_info in result['share_links']:
                share_links_data.append(ShareLinkData(
                    share_id=link_info['share_id'],
                    url=link_info['url'],
                    station_slug=link_info['station_slug'],
                    station_title=link_info['station_title'],
                    visit_count=link_info['visit_count'],
                    created_at=link_info['created_at'],
                    is_active=link_info['is_active']
                ))
            
            return GetShareLinksResponse(
                success=True,
                message=f"Found {len(share_links_data)} share links",
                user_id=user_id,
                share_links=share_links_data
            )
            
        except Exception as e:
            logger.error(f"Error getting share links: {e}")
            return GetShareLinksResponse(
                success=False,
                message=f"Error getting share links: {str(e)}",
                user_id=user_id
            )
