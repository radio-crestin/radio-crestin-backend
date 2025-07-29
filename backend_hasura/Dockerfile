FROM docker.io/hasura/graphql-engine:v2.33.4.cli-migrations-v3

# Copy Hasura configuration and metadata
COPY config.yaml /hasura-config/config.yaml
COPY metadata /hasura-metadata
COPY seeds /hasura-seeds

# Create migrations directory structure if it doesn't exist
# This prevents errors when no migrations are present
RUN mkdir -p /hasura-migrations/default

# Copy migrations only if they exist, otherwise create empty structure
COPY migrations /hasura-migrations

# Set the working directory for Hasura CLI
WORKDIR /hasura-config

# The base image with cli-migrations-v3 tag automatically:
# 1. Applies migrations from /hasura-migrations on startup
# 2. Applies metadata from /hasura-metadata on startup
# 3. Starts the GraphQL engine
# No additional configuration needed