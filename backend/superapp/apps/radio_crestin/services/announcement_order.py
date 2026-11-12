"""Reordering announcements from the admin list, which may show only some of them.

The list can be filtered, searched or paged, so a drag renumbers just the visible
rows (0, 1, 2, ...). Those rows get back the same set of positions they held, in
their new order; every other announcement keeps its own. Positions stay unique.
"""
from django.db import transaction

from ..models import Announcement
from . import web_deploy
from .announcement_feed import invalidate_cache


def _unique_positions() -> dict:
    """{id: position}, first renumbering every row 0..n-1 (same order) if any position is shared."""
    rows = list(Announcement.objects.select_for_update().order_by('position', 'id').values_list('id', 'position'))
    positions = [position for _, position in rows]
    if len(set(positions)) == len(positions):
        return dict(rows)
    for index, (announcement_id, position) in enumerate(rows):
        if position != index:
            Announcement.objects.filter(id=announcement_id).update(position=index)
    return {announcement_id: index for index, (announcement_id, _) in enumerate(rows)}


def reorder(visible_ids_in_new_order) -> int:
    """Gives the visible rows, in their new order, the positions they held; returns how many rows moved.

    One transaction, rows written with update() (no per-row signals): the cached API list
    is dropped once afterwards, and the website rebuild is scheduled once.
    """
    ids = list(dict.fromkeys(visible_ids_in_new_order))
    with transaction.atomic():
        current = _unique_positions()
        ids = [announcement_id for announcement_id in ids if announcement_id in current]
        slots = sorted(current[announcement_id] for announcement_id in ids)
        moved = 0
        for announcement_id, slot in zip(ids, slots):
            if current[announcement_id] != slot:
                Announcement.objects.filter(id=announcement_id).update(position=slot)
                moved += 1
        transaction.on_commit(invalidate_cache)
        web_deploy.schedule()
    return moved
