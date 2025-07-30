# Django SuperApp - GraphQL
### Getting Started
1. Setup the project using the instructions from https://django-superapp.bringes.io/
2. Setup `graphql` app using the below instructions:
```bash
cd my_superapp;
cd superapp/apps;
django_superapp bootstrap-app \
    --template-repo https://github.com/django-superapp/django-superapp-graphql ./graphql;
cd ../../;
```
3. The created `graphql` app will search for `graphql` folder in each installed apps and it will expose them as GraphQL APIs.
  - for example, you can copy `./sample_graphql` folder in your app and then start by updating it based on your requirements
4. The documentation on how to configure the graphql app is available at https://strawberry.rocks/docs/django

### CORS Configuration

All GraphQL endpoints (`/graphql`, `/v1/graphql`, `/v2/graphql`) have CORS (Cross-Origin Resource Sharing) enabled using a custom `cors_exempt` decorator, similar to Django's `csrf_exempt`.

#### Configuration Options

The CORS behavior can be configured using environment variables:

1. **Allow all origins** (not recommended for production):
   ```bash
   GRAPHQL_CORS_ALLOW_ALL_ORIGINS=true
   ```

2. **Allow specific origins** (recommended):
   ```bash
   GRAPHQL_CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com,http://localhost:3000
   ```

If neither environment variable is set, the following origins are allowed by default:
- http://localhost:3000
- http://localhost:8080
- http://localhost:8081
- http://127.0.0.1:3000
- http://127.0.0.1:8080
- http://127.0.0.1:8081

#### Features

- Custom `cors_exempt` decorator that works like Django's `csrf_exempt`
- Handles preflight OPTIONS requests automatically
- Allows credentials in CORS requests
- Supports all standard headers plus Apollo Client headers
- 24-hour cache for preflight requests

#### Security Note

For production environments, always use `GRAPHQL_CORS_ALLOWED_ORIGINS` with specific trusted domains instead of allowing all origins.
