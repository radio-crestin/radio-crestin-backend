from typing import Optional, Dict, Any
from django.db import transaction
import logging

from ..models import Reviews, Stations

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
        user_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a review for a station.

        Reviews are unique per station and IP address. If the same IP submits
        another review for the same station, the existing review is updated.

        Args:
            station_id: The ID of the station being reviewed
            ip_address: The IP address of the reviewer
            stars: Rating from 0 to 5
            message: Optional review message
            user_identifier: Optional unique identifier from the client

        Returns:
            Dict containing review info and whether it was created or updated
        """
        try:
            station = Stations.objects.get(id=station_id)
        except Stations.DoesNotExist:
            raise ValueError(f"Station with ID {station_id} not found")

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
            defaults=review_data
        )

        action = "created" if created else "updated"
        logger.info(
            f"Review {action} for station {station.title} from IP {ip_address}"
        )

        return {
            'review': {
                'id': review.id,
                'station_id': review.station_id,
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
    def delete(station_id: int, ip_address: str) -> bool:
        """
        Delete a review by station and IP address.

        Args:
            station_id: The ID of the station
            ip_address: The IP address of the reviewer

        Returns:
            True if deleted, False if not found
        """
        try:
            review = Reviews.objects.get(
                station_id=station_id,
                ip_address=ip_address
            )
            review.delete()
            logger.info(
                f"Review deleted for station {station_id} from IP {ip_address}"
            )
            return True
        except Reviews.DoesNotExist:
            return False
