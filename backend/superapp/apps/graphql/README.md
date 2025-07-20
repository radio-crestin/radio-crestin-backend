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
