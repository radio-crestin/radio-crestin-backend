from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import AppUsers, ShareLink, ShareLinkVisit, Stations
from ..models.share_links import generate_share_id


class ShareLinkService:
    """Service for managing share links and tracking visits."""
    
    @staticmethod
    @transaction.atomic
    def upsert_user(
        anonymous_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> AppUsers:
        """
        Upsert a user based on anonymous_id.
        Creates a new user if not exists, updates if exists.
        """
        user_data = {
            'anonymous_id': anonymous_id,
        }
        
        # Add optional fields if provided
        if first_name is not None:
            user_data['first_name'] = first_name
        if last_name is not None:
            user_data['last_name'] = last_name
        if email is not None:
            user_data['email'] = email
            
        # Update timestamp for existing users
        user_data['updated_at'] = timezone.now()
        
        # Upsert user
        user, created = AppUsers.objects.update_or_create(
            anonymous_id=anonymous_id,
            defaults=user_data
        )
        
        # Set created_at for new users
        if created:
            user.created_at = timezone.now()
            user.save(update_fields=['created_at'])
        
        return user
    
    @staticmethod
    @transaction.atomic
    def upsert_share_link(
        user: AppUsers,
        station: Optional[Stations] = None
    ) -> ShareLink:
        """
        Create or get a share link for a user and optional station.
        Returns existing link if one exists for the same user/station combination.
        """
        # Try to find existing share link for this user/station combination
        share_link = ShareLink.objects.filter(
            user=user,
            station=station,
            is_active=True
        ).first()
        
        if share_link:
            # Return existing share link
            return share_link
        
        # Create new share link with unique ID
        share_link = ShareLink.objects.create(
            share_id=generate_share_id(),
            user=user,
            station=station
        )
        
        return share_link
    
    @staticmethod
    def get_share_link_info(user_id: str) -> Dict[str, Any]:
        """
        Get share link information for a user including visitor counts.
        """
        try:
            user = AppUsers.objects.get(anonymous_id=user_id)
        except AppUsers.DoesNotExist:
            return {
                'error': 'User not found',
                'share_links': []
            }
        
        share_links = ShareLink.objects.filter(
            user=user,
            is_active=True
        ).select_related('station')
        
        result = {
            'user_id': user_id,
            'share_links': []
        }
        
        for link in share_links:
            link_data = {
                'share_id': link.share_id,
                'url': link.get_full_url(),
                'station_slug': link.station.slug if link.station else None,
                'station_title': link.station.title if link.station else None,
                'visit_count': link.visit_count,
                'created_at': link.created_at.isoformat(),
                'is_active': link.is_active
            }
            result['share_links'].append(link_data)
        
        return result
    
    @staticmethod
    @transaction.atomic
    def track_visit(
        share_id: str,
        visitor_ip: Optional[str] = None,
        visitor_user_agent: Optional[str] = None,
        visitor_referer: Optional[str] = None,
        visitor_session_id: Optional[str] = None
    ) -> Optional[ShareLinkVisit]:
        """
        Track a visit to a share link.
        Returns None if share link not found or inactive.
        """
        try:
            share_link = ShareLink.objects.select_for_update().get(
                share_id=share_id,
                is_active=True
            )
        except ShareLink.DoesNotExist:
            return None
        
        # Check if this is a unique visit (not from the creator)
        # We use session_id to track unique visitors within a session
        if visitor_session_id:
            # Check if this session has already visited this link
            existing_visit = ShareLinkVisit.objects.filter(
                share_link=share_link,
                visitor_session_id=visitor_session_id
            ).exists()
            
            if existing_visit:
                # Not a new unique visit, don't increment counter
                return None
        
        # Create visit record
        visit = ShareLinkVisit.objects.create(
            share_link=share_link,
            visitor_ip=visitor_ip,
            visitor_user_agent=visitor_user_agent,
            visitor_referer=visitor_referer,
            visitor_session_id=visitor_session_id
        )
        
        # Increment visit count atomically
        share_link.increment_visit_count()
        
        return visit
    
    @staticmethod
    def delete_share_link(share_id: str) -> bool:
        """
        Soft delete a share link by marking it as inactive.
        """
        try:
            share_link = ShareLink.objects.get(share_id=share_id)
            share_link.is_active = False
            share_link.save(update_fields=['is_active', 'updated_at'])
            return True
        except ShareLink.DoesNotExist:
            return False
    
    @staticmethod
    def get_share_link_by_id(share_id: str) -> Optional[ShareLink]:
        """
        Get a share link by its ID.
        """
        try:
            return ShareLink.objects.select_related('station', 'user').get(
                share_id=share_id,
                is_active=True
            )
        except ShareLink.DoesNotExist:
            return None