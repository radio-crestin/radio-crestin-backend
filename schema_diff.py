#!/usr/bin/env python3
"""
GraphQL Schema Comparison Script
Fetches schemas from remote and local endpoints, compares them, and outputs differences.
"""

import json
import requests
import sys
from typing import Dict, Any, List
from difflib import unified_diff
import argparse


def fetch_graphql_schema(endpoint: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Fetch GraphQL schema from an endpoint using introspection query."""
    
    introspection_query = """
    query IntrospectionQuery {
      __schema {
        queryType { name }
        mutationType { name }
        subscriptionType { name }
        types {
          ...FullType
        }
        directives {
          name
          description
          locations
          args {
            ...InputValue
          }
        }
      }
    }
    
    fragment FullType on __Type {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          ...InputValue
        }
        type {
          ...TypeRef
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        ...InputValue
      }
      interfaces {
        ...TypeRef
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        ...TypeRef
      }
    }
    
    fragment InputValue on __InputValue {
      name
      description
      type { ...TypeRef }
      defaultValue
    }
    
    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    payload = {
        "query": introspection_query
    }
    
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers or {"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        if "errors" in result:
            print(f"GraphQL errors from {endpoint}: {result['errors']}")
            return None
            
        return result.get("data", {}).get("__schema")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schema from {endpoint}: {e}")
        return None


def normalize_schema(schema: Dict[str, Any]) -> str:
    """Convert schema to normalized string format for comparison."""
    if not schema:
        return ""
    
    # Sort types by name for consistent comparison
    if "types" in schema:
        schema["types"] = sorted(schema["types"], key=lambda x: x.get("name", ""))
        
        # Sort fields within each type
        for type_def in schema["types"]:
            if type_def.get("fields"):
                type_def["fields"] = sorted(type_def["fields"], key=lambda x: x.get("name", ""))
            if type_def.get("inputFields"):
                type_def["inputFields"] = sorted(type_def["inputFields"], key=lambda x: x.get("name", ""))
            if type_def.get("enumValues"):
                type_def["enumValues"] = sorted(type_def["enumValues"], key=lambda x: x.get("name", ""))
    
    return json.dumps(schema, indent=2, sort_keys=True)


def generate_diff(remote_schema: str, local_schema: str) -> List[str]:
    """Generate unified diff between two schemas."""
    remote_lines = remote_schema.splitlines(keepends=True)
    local_lines = local_schema.splitlines(keepends=True)
    
    return list(unified_diff(
        remote_lines,
        local_lines,
        fromfile="remote_schema.json",
        tofile="local_schema.json",
        lineterm=""
    ))


def save_schemas(remote_schema: str, local_schema: str, diff_lines: List[str]):
    """Save schemas and diff to files."""
    with open("remote_schema.json", "w") as f:
        f.write(remote_schema)
    
    with open("local_schema.json", "w") as f:
        f.write(local_schema)
    
    with open("schema_diff.txt", "w") as f:
        f.writelines(diff_lines)


def main():
    parser = argparse.ArgumentParser(description="Compare GraphQL schemas")
    parser.add_argument("--remote", default="https://graphql.radio-crestin.com/v1/graphql", 
                       help="Remote GraphQL endpoint")
    parser.add_argument("--local", default="http://localhost:8080/graphql", 
                       help="Local GraphQL endpoint")
    parser.add_argument("--save", action="store_true", 
                       help="Save schemas and diff to files")
    
    args = parser.parse_args()
    
    print(f"Fetching remote schema from: {args.remote}")
    remote_schema = fetch_graphql_schema(args.remote)
    
    print(f"Fetching local schema from: {args.local}")
    local_schema = fetch_graphql_schema(args.local)
    
    if not remote_schema:
        print("Failed to fetch remote schema")
        sys.exit(1)
    
    if not local_schema:
        print("Failed to fetch local schema")
        sys.exit(1)
    
    # Normalize schemas for comparison
    remote_normalized = normalize_schema(remote_schema)
    local_normalized = normalize_schema(local_schema)
    
    # Generate diff
    diff_lines = generate_diff(remote_normalized, local_normalized)
    
    if not diff_lines:
        print("✅ Schemas are identical!")
    else:
        print("🔍 Schema differences found:")
        print("".join(diff_lines))
    
    if args.save:
        save_schemas(remote_normalized, local_normalized, diff_lines)
        print("\n📁 Files saved:")
        print("  - remote_schema.json")
        print("  - local_schema.json")
        print("  - schema_diff.txt")


if __name__ == "__main__":
    main()