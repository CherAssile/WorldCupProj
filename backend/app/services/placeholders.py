"""Libellés lisibles des placeholders de phase finale.

Le format source (openfootball) est `W<num>` (vainqueur du match num) ou `L<num>`
(perdant). Le backend expose le libellé résolu pour que le frontend n'ait jamais à
décoder le code brut.
"""
from __future__ import annotations

import re

_PLACEHOLDER_PATTERN = re.compile(r"^([WL])(\d+)$")


def placeholder_label(code: str | None) -> str | None:
    """« W101 » → « Vainqueur du match 101 », « L102 » → « Perdant du match 102 ».
    Retombe sur le code brut si le format est inattendu, None si pas de placeholder."""
    if code is None:
        return None
    match = _PLACEHOLDER_PATTERN.match(code)
    if match is None:
        return code
    kind, num = match.groups()
    return f"Vainqueur du match {num}" if kind == "W" else f"Perdant du match {num}"
