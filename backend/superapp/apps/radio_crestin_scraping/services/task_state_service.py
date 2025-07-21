import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.db import transaction

from ..models import StationScrapingTaskState
from ...radio_crestin.models import Stations
from ..utils.data_types import StationNowPlayingData

logger = logging.getLogger(__name__)


class TaskStateService:
    """Service to manage station scraping task states and prevent race conditions"""
    
    @staticmethod
    def initialize_task_state(station_id: int, task_id: str) -> Dict[str, Any]:
        """Initialize or update task state for a station"""
        try:
            with transaction.atomic():
                station = Stations.objects.get(id=station_id)
                task_state, created = StationScrapingTaskState.objects.get_or_create(
                    station=station,
                    defaults={
                        'current_task_id': task_id,
                        'current_task_started_at': timezone.now(),
                        'processed_fetcher_states': {}
                    }
                )
                
                if not created:
                    # Check if we should override current task
                    current_time = timezone.now()
                    if (task_state.current_task_started_at and 
                        (current_time - task_state.current_task_started_at).total_seconds() > 300):
                        # Override if current task is older than 5 minutes (likely stale)
                        logger.warning(f"Overriding stale task {task_state.current_task_id} with {task_id}")
                        task_state.current_task_id = task_id
                        task_state.current_task_started_at = current_time
                        task_state.processed_fetcher_states = {}
                        task_state.save()
                    elif task_state.current_task_id != task_id:
                        # Another task is already running
                        logger.info(f"Task {task_id} skipped - task {task_state.current_task_id} already running")
                        return {
                            'should_continue': False,
                            'reason': f'Another task ({task_state.current_task_id}) is already running',
                            'task_state': task_state
                        }
                
                return {
                    'should_continue': True,
                    'task_state': task_state
                }
                
        except Exception as error:
            logger.error(f"Error initializing task state for station {station_id}: {error}")
            return {
                'should_continue': False,
                'reason': f'Error initializing task state: {str(error)}',
                'task_state': None
            }
    
    @staticmethod
    def process_fetcher_result(
        task_state: StationScrapingTaskState,
        fetcher_id: int,
        fetcher_order: int,
        scrape_result: StationNowPlayingData,
        task_id: str
    ) -> Dict[str, Any]:
        """Process and save individual fetcher result with priority-based merging"""
        try:
            with transaction.atomic():
                # Refresh task state to get latest data
                task_state.refresh_from_db()
                
                # Verify this task should still be running
                if task_state.current_task_id != task_id:
                    return {
                        'success': False,
                        'reason': f'Task {task_id} was superseded by {task_state.current_task_id}',
                        'should_abort': True
                    }
                
                current_time = timezone.now()
                fetcher_state = {
                    'status': 'completed',
                    'priority': fetcher_order,
                    'data': scrape_result.model_dump() if hasattr(scrape_result, 'model_dump') else scrape_result.__dict__,
                    'timestamp': current_time.isoformat(),
                    'task_id': task_id
                }
                
                # Update processed fetchers
                if not isinstance(task_state.processed_fetcher_states, dict):
                    task_state.processed_fetcher_states = {}
                
                task_state.processed_fetcher_states[str(fetcher_id)] = fetcher_state
                task_state.save()
                
                # Merge data based on priority
                merged_data = TaskStateService._merge_priority_data(task_state)
                
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'should_abort': False
                }
                
        except Exception as error:
            logger.error(f"Error processing fetcher result: {error}")
            return {
                'success': False,
                'reason': f'Error processing fetcher result: {str(error)}',
                'should_abort': False
            }
    
    @staticmethod
    def mark_fetcher_failed(
        task_state: StationScrapingTaskState,
        fetcher_id: int,
        fetcher_order: int,
        error_message: str,
        task_id: str
    ) -> None:
        """Mark a fetcher as failed in the task state"""
        try:
            with transaction.atomic():
                task_state.refresh_from_db()
                
                if task_state.current_task_id != task_id:
                    return  # Task was superseded
                
                current_time = timezone.now()
                fetcher_state = {
                    'status': 'failed',
                    'priority': fetcher_order,
                    'error': error_message,
                    'timestamp': current_time.isoformat(),
                    'task_id': task_id
                }
                
                if not isinstance(task_state.processed_fetcher_states, dict):
                    task_state.processed_fetcher_states = {}
                
                task_state.processed_fetcher_states[str(fetcher_id)] = fetcher_state
                task_state.save()
                
        except Exception as error:
            logger.error(f"Error marking fetcher as failed: {error}")
    
    @staticmethod
    def finalize_task(
        task_state: StationScrapingTaskState,
        task_id: str,
        success: bool,
        final_data: Optional[StationNowPlayingData] = None
    ) -> None:
        """Finalize task state and update success tracking"""
        try:
            with transaction.atomic():
                task_state.refresh_from_db()
                
                if task_state.current_task_id != task_id:
                    return  # Task was superseded
                
                if success and final_data:
                    task_state.last_successful_update_at = timezone.now()
                    task_state.last_successful_task_id = task_id
                
                # Clear current task since it's completed
                task_state.current_task_id = None
                task_state.current_task_started_at = None
                task_state.save()
                
        except Exception as error:
            logger.error(f"Error finalizing task: {error}")
    
    @staticmethod
    def _merge_priority_data(task_state: StationScrapingTaskState) -> Optional[StationNowPlayingData]:
        """Merge data from completed fetchers based on priority (lower order = higher priority)"""
        if not task_state.processed_fetcher_states:
            return None
        
        # Get completed fetchers sorted by priority
        completed_fetchers = []
        for fetcher_id, state in task_state.processed_fetcher_states.items():
            if state.get('status') == 'completed' and 'data' in state:
                completed_fetchers.append((state['priority'], state['data']))
        
        if not completed_fetchers:
            return None
        
        # Sort by priority (lower order = higher priority)
        completed_fetchers.sort(key=lambda x: x[0])
        
        # Start with the highest priority data
        base_data_dict = completed_fetchers[0][1]
        
        # Reconstruct StationNowPlayingData from dict
        try:
            merged_data = StationNowPlayingData(**base_data_dict)
        except Exception:
            # Fallback if data structure doesn't match
            logger.warning("Could not reconstruct StationNowPlayingData, using dict merge")
            merged_data = base_data_dict
            
            # Simple dict-based merge for remaining fetchers
            for priority, data_dict in completed_fetchers[1:]:
                if isinstance(merged_data, dict) and isinstance(data_dict, dict):
                    # Merge raw_data and error arrays
                    if 'raw_data' in data_dict and data_dict['raw_data']:
                        if 'raw_data' not in merged_data:
                            merged_data['raw_data'] = []
                        merged_data['raw_data'].extend(data_dict['raw_data'])
                    
                    if 'error' in data_dict and data_dict['error']:
                        if 'error' not in merged_data:
                            merged_data['error'] = []
                        merged_data['error'].extend(data_dict['error'])
                    
                    # Update timestamp to latest
                    if 'timestamp' in data_dict:
                        merged_data['timestamp'] = data_dict['timestamp']
            
            return merged_data
        
        # Merge additional data from lower priority fetchers
        for priority, data_dict in completed_fetchers[1:]:
            try:
                new_data = StationNowPlayingData(**data_dict)
                merged_data = TaskStateService._merge_station_data(merged_data, new_data)
            except Exception:
                logger.warning(f"Could not merge data from priority {priority}")
                continue
        
        return merged_data
    
    @staticmethod
    def _merge_station_data(base_data: StationNowPlayingData, new_data: StationNowPlayingData) -> StationNowPlayingData:
        """Merge two StationNowPlayingData objects, preserving higher priority data"""
        # Merge raw_data arrays
        if new_data.raw_data:
            base_data.raw_data.extend(new_data.raw_data)

        # Merge error arrays
        if new_data.error:
            base_data.error.extend(new_data.error)

        # Only override if base data doesn't have the field or it's empty
        if new_data.current_song and new_data.current_song.name and (
            not base_data.current_song or not base_data.current_song.name
        ):
            base_data.current_song = new_data.current_song

        if new_data.listeners is not None and base_data.listeners is None:
            base_data.listeners = new_data.listeners

        # Update timestamp to latest
        base_data.timestamp = new_data.timestamp

        return base_data