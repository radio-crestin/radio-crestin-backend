"""
Dynamic REST endpoint registration

This module automatically discovers and registers REST API endpoints from all installed apps.
"""

import importlib
import os
from typing import List, Type

from django.apps import apps

from superapp.apps.graphql.rest_api import RestApiEndpoint, RestApiRegistry


def discover_and_register_rest_endpoints() -> List[Type[RestApiEndpoint]]:
    """
    Discover and register all REST API endpoints from installed apps
    
    Looks for 'graphql/rest_endpoints.py' in each app and registers any
    endpoints found in the REST_ENDPOINTS list.
    
    Returns:
        List of registered endpoint classes
    """
    registered_endpoints = []
    
    for app_config in apps.get_app_configs():
        app_path = app_config.path
        rest_endpoints_path = os.path.join(app_path, 'graphql', 'rest_endpoints.py')
        
        # Check if rest_endpoints.py exists
        if os.path.exists(rest_endpoints_path):
            try:
                # Import the rest_endpoints module
                module = importlib.import_module(f"{app_config.name}.graphql.rest_endpoints")
                
                # Look for REST_ENDPOINTS list
                if hasattr(module, 'REST_ENDPOINTS'):
                    endpoints = getattr(module, 'REST_ENDPOINTS')
                    
                    # Register each endpoint class
                    for endpoint_class in endpoints:
                        try:
                            if issubclass(endpoint_class, RestApiEndpoint):
                                RestApiRegistry.register_endpoint_class(endpoint_class)
                                registered_endpoints.append(endpoint_class)
                                print(f"Registered REST endpoint: {endpoint_class.__name__} from {app_config.name}")
                        except Exception as e:
                            print(f"Error registering endpoint {endpoint_class.__name__}: {e}")
                
            except ImportError as e:
                print(f"Could not import rest_endpoints from {app_config.name}: {e}")
                continue
            except Exception as e:
                print(f"Error loading rest_endpoints from {app_config.name}: {e}")
                continue
    
    return registered_endpoints


# Auto-discover and register endpoints when this module is imported
discover_and_register_rest_endpoints()