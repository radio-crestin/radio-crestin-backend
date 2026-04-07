from typing import Optional, Dict, Any
from django.db import transaction
import logging

from ..models import Reviews, Stations, Songs

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing station reviews."""

    @staticmethod
    @transaction.atomic
    def upsert(
        station_id: int,
        ip_address: str,
        stars: int,
        message: Optional[str] = None,
        user_identifier: Optional[str] = None,
        song_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create or update a review for a station, optionally for a specific song.

        Reviews are unique per (station, ip_address, song). A user can leave one
        review per station without a song, and one review per station+song combination.

        Args:
            station_id: The ID of the station being reviewed
            ip_address: The IP address of the reviewer
            stars: Rating from 0 to 5
            message: Optional review message
            user_identifier: Optional unique identifier from the client
            song_id: Optional song ID to associate the review with

        Returns:
            Dict containing review info and whether it was created or updated
        """
        try:
            station = Stations.objects.get(id=station_id)
        except Stations.DoesNotExist:
            raise ValueError(f"Station with ID {station_id} not found")

        song = None
        if song_id:
            try:
                song = Songs.objects.get(id=song_id)
            except Songs.DoesNotExist:
                raise ValueError(f"Song with ID {song_id} not found")

        # Clamp stars between 0 and 5
        stars = max(0, min(5, stars))

        review_data = {
            'stars': stars,
            'message': message,
        }

        if user_identifier:
            review_data['user_identifier'] = user_identifier

        review, created = Reviews.objects.update_or_create(
            station=station,
            ip_address=ip_address,
            song=song,
            defaults=review_data
        )

        action = "created" if created else "updated"
        logger.info(
            f"Review {action} for station {station.title} (song={song_id}) from IP {ip_address}"
        )

        return {
            'review': {
                'id': review.id,
                'station_id': review.station_id,
                'song_id': review.song_id,
                'stars': review.stars,
                'message': review.message,
                'user_identifier': review.user_identifier,
                'created_at': review.created_at.isoformat(),
                'updated_at': review.updated_at.isoformat(),
                'verified': review.verified,
            },
            'created': created,
        }

    @staticmethod
    @transaction.atomic
    def delete(station_id: int, ip_address: str, song_id: Optional[int] = None) -> bool:
        """
        Delete a review by station, IP address, and optionally song.

        Args:
            station_id: The ID of the station
            ip_address: The IP address of the reviewer
            song_id: Optional song ID

        Returns:
            True if deleted, False if not found
        """
        try:
            review = Reviews.objects.get(
                station_id=station_id,
                ip_address=ip_address,
                song_id=song_id
            )
            review.delete()
            logger.info(
                f"Review deleted for station {station_id} (song={song_id}) from IP {ip_address}"
            )
            return True
        except Reviews.DoesNotExist:
            return False
