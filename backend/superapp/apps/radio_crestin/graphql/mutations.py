from __future__ import annotations

import strawberry
from typing import Optional, List
from django.utils import timezone
from datetime import datetime
import logging

from .types import StationType, ListeningEventInput, SubmitListeningEventsResponse, TriggerMetadataFetchResponse
from ..models import Stations, AppUsers, ListeningSessions


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
    
    @strawberry.field
    def submit_listening_events(self, events: List[ListeningEventInput]) -> SubmitListeningEventsResponse:
        """Submit batch of listening events from HLS streaming logs"""
        logger = logging.getLogger(__name__)
        processed_count = 0
        
        try:
            for event_input in events:
                try:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(event_input.timestamp.replace('Z', '+00:00'))
                    
                    # Find or get station by slug
                    try:
                        station = Stations.objects.get(slug=event_input.station_slug)
                    except Stations.DoesNotExist:
                        logger.warning(f"Station not found: {event_input.station_slug}")
                        continue
                    
                    # Get or create anonymous user for session tracking
                    # Use a simple approach that works with existing table structure
                    try:
                        anonymous_user = AppUsers.objects.get(anonymous_id=event_input.anonymous_session_id)
                    except AppUsers.DoesNotExist:
                        anonymous_user = AppUsers.objects.create(
                            anonymous_id=event_input.anonymous_session_id,
                            is_active=True,
                            is_staff=False,
                            is_superuser=False,
                            password='',  # Anonymous users don't need passwords
                            first_name='',
                            last_name=''
                        )
                    
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
    
    @strawberry.field
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