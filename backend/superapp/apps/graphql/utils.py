from enum import Enum

import strawberry
from django.db import models


def textchoices_to_strawberry_enum(textchoices_cls: type[models.TextChoices], use_labels_as_description=True):
    """
    Converts a Django TextChoices class to a Strawberry enum.

    Args:
        textchoices_cls: The Django TextChoices class to convert.
        use_labels_as_description: Whether to use the labels as descriptions in the enum.

    Returns:
        A Strawberry GraphQL enum.
    """
    enum_members = {}
    for member in textchoices_cls:
        if use_labels_as_description:
            enum_members[member.name] = strawberry.enum_value(
                member.value,
                description=str(member.label)  # Force to plain string
            )
        else:
            enum_members[member.name] = member.value

    dynamic_enum = Enum(textchoices_cls.__name__, enum_members)
    return strawberry.enum(dynamic_enum)
