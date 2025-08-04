from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import AppUsers, ShareLink, ShareLinkVisit
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
    def upsert_share_link(user: AppUsers) -> ShareLink:
        """
        Create or get the unique share link for a user.
        Each user has exactly one share link.
        """
        # Try to get existing share link for this user
        try:
            share_link = ShareLink.objects.get(user=user)
            # Ensure it's active
            if not share_link.is_active:
                share_link.is_active = True
                share_link.save(update_fields=['is_active', 'updated_at'])
            return share_link
        except ShareLink.DoesNotExist:
            # Create new share link with unique ID
            share_link = ShareLink.objects.create(
                share_id=generate_share_id(),
                user=user
            )
            return share_link
    
    @staticmethod
    @transaction.atomic
    def get_share_link_info(user_id: str) -> Dict[str, Any]:
        """
        Get the unique share link information for a user.
        Creates user and share link if they don't exist.
        """
        # Upsert user if not exists
        user = ShareLinkService.upsert_user(anonymous_id=user_id)
        
        # Get or create share link for the user
        share_link = ShareLinkService.upsert_share_link(user=user)
        
        return {
            'user_id': user_id,
            'share_link': {
                'share_id': share_link.share_id,
                'base_url': share_link.get_full_url(),
                'visit_count': share_link.visit_count,
                'created_at': share_link.created_at.isoformat(),
                'is_active': share_link.is_active
            }
        }
    
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
            return ShareLink.objects.select_related('user').get(
                share_id=share_id,
                is_active=True
            )
        except ShareLink.DoesNotExist:
            return None