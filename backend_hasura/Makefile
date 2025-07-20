fresh-install:
	make apply-hasura-metadata;
	make apply-hasura-migrations;
	make apply-hasura-metadata;

start-hasura-console:
	kill $(lsof -t -i:9695); \
	hasura console --envfile .env

start-hasura-console-remote:
	kill $(lsof -t -i:9695); \
	hasura console --envfile .env.remote --endpoint https://graphql.radio-crestin.com

apply-hasura-migrations:
	hasura migrate apply --all-databases  --envfile .env

apply-hasura-metadata:
	hasura metadata apply  --envfile .env; \
	hasura metadata reload  --envfile .env; \
	hasura metadata ic list  --envfile .env;

list-hasura-metadata-list-inconsistency: apply-hasura-metadata
	hasura metadata inconsistency list  --envfile .env

squash-hasura-migrations:
	hasura migrate squash --delete-source --from 1648886276821 --envfile .env


reload-hasura-metadata:
	hasura metadata reload --endpo
