from strawberry.extensions import Extension
from typing import Any, Dict

from superapp.apps.radio_crestin.graphql.dataloaders import (
    create_listener_count_loader,
    create_posts_loader
)


class DataLoaderExtension(Extension):
    """
    Extension to add DataLoaders to the GraphQL context.
    This enables efficient batch loading of related data.
    """
    
    def on_request_start(self) -> None:
        """Initialize DataLoaders at the start of each request"""
        # Create DataLoader instances
        listener_count_loader = create_listener_count_loader()
        posts_loader_single = create_posts_loader(limit=1)  # For single post queries
        posts_loader_multiple = create_posts_loader(limit=10)  # For multiple posts queries
        
        # Add to execution context
        self.execution_context.context.listener_count_loader = listener_count_loader
        self.execution_context.context.posts_loader_single = posts_loader_single
        self.execution_context.context.posts_loader_multiple = posts_loader_multiple