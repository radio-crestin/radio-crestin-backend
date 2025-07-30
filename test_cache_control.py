#!/usr/bin/env python
"""
Test script to verify cache control headers are being set correctly in GraphQL responses.
Run this after starting your Django server.
"""

import requests
import json

# Configuration
GRAPHQL_URL = "http://localhost:8080/v1/graphql"  # Using the GraphQLProxyView endpoint

# Test queries with cache control directive
test_queries = [
    {
        "name": "Simple cache control",
        "query": """
        query TestQuery @cache_control(max_age: 300) {
            __typename
        }
        """,
        "expected_header": "max-age=300"
    },
    {
        "name": "No cache directive",
        "query": """
        query TestQuery @cache_control(no_cache: true) {
            __typename
        }
        """,
        "expected_header": "no-cache"
    },
    {
        "name": "Public cache with max age",
        "query": """
        query TestQuery @cache_control(max_age: 600, public: true) {
            __typename
        }
        """,
        "expected_header": "public, max-age=600"
    },
    {
        "name": "Complex cache control",
        "query": """
        query TestQuery @cache_control(
            max_age: 300, 
            stale_while_revalidate: 60,
            public: true
        ) {
            __typename
        }
        """,
        "expected_header": "public, max-age=300, stale-while-revalidate=60"
    }
]

def test_cache_control():
    """Test cache control headers"""
    print("Testing Cache Control Headers\n" + "="*50)
    
    for test in test_queries:
        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query'].strip()}")
        
        # Make request
        response = requests.post(
            GRAPHQL_URL,
            json={"query": test['query']},
            headers={"Content-Type": "application/json"}
        )
        
        # Check response
        print(f"Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        cache_control = response.headers.get('Cache-Control', 'NOT SET')
        print(f"Cache-Control header: {cache_control}")
        print(f"Expected: {test['expected_header']}")
        
        if cache_control == test['expected_header']:
            print("✅ PASS")
        else:
            print("❌ FAIL")
        
        # Show response body if there's an error
        if response.status_code != 200:
            print(f"Response body: {response.text}")
        else:
            data = response.json()
            if 'errors' in data:
                print(f"GraphQL errors: {data['errors']}")

if __name__ == "__main__":
    test_cache_control()