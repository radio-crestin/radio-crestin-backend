import strawberry

try:
    # Django-channels is not always used/intalled,
    # therefore it shouldn't be it a hard requirement.
    from channels import auth as channels_auth
except ModuleNotFoundError:
    channels_auth = None


@strawberry.type
class Query:
    @strawberry.field
    def sample_query(self, info: strawberry.Info) -> str:
        return "sample query response here"
