"""current_user never returns the password hash."""

from django.test import SimpleTestCase

from superapp.apps.graphql.schema import schema


class CurrentUserFieldsTests(SimpleTestCase):
    def test_password_is_not_a_field(self):
        result = schema.execute_sync('{ current_user { password } }')
        self.assertIn("Cannot query field 'password'", result.errors[0].message)
