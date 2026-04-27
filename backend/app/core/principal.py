"""Owner principal — single-owner identity carried through request scope."""

from __future__ import annotations

from dataclasses import dataclass

OWNER_ID = 1


@dataclass(frozen=True, slots=True)
class OwnerPrincipal:
    """Authenticated single-owner principal.

    Carries only the static owner identifier — no DB-backed user row exists.
    Construct via ``OwnerPrincipal()`` and use ``principal.id`` like a User.id.
    """

    id: int = OWNER_ID
