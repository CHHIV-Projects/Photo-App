"""Policy helpers for provider writes to canonical Place fields."""

from __future__ import annotations

from app.models.place import Place


def should_block_provider_canonical_overwrite(place: Place) -> bool:
    """Block provider overwrites when the place has been user-reviewed or locked."""
    return bool(place.user_verified or place.address_locked)
