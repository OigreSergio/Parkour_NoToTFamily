"""Decodifica delle geometrie PostGIS ricevute via REST.

Serve per lo schema delle migrazioni del repository
(`supabase/migrations/0001_initial.sql`), dove `spots.location` è una
`geography(Point, 4326)`. Lo schema reale di produzione, letto dal backup
pubblico, ha invece due colonne numeriche `lat` e `lng` e non passa di qui.

Via PostgREST una geografia può arrivare in due forme, entrambe accettate:

1. come GeoJSON (`{"type": "Point", "coordinates": [lng, lat]}`), se il
   client chiede `Accept: application/geo+json` o la colonna è già convertita;
2. come stringa esadecimale EWKB (Extended Well-Known Binary), la forma
   "grezza" di PostGIS: `0101000020E6100000<8 byte x><8 byte y>`.

Il parser EWKB qui sotto gestisce solo i punti, che è tutto ciò che serve.
"""

import math
import struct
from typing import Any

# Bit del campo "tipo" di EWKB che dicono se seguono lo SRID o le coordinate Z/M.
_SRID_FLAG = 0x20000000
_Z_FLAG = 0x80000000
_M_FLAG = 0x40000000
_POINT_TYPE = 1


def parse_ewkb_point(hex_text: str) -> tuple[float, float]:
    """Da EWKB esadecimale a `(lat, lng)`. Alza `ValueError` se non è un punto."""
    try:
        raw = bytes.fromhex(hex_text)
    except ValueError as exc:
        raise ValueError("EWKB non esadecimale") from exc
    if len(raw) < 21:
        raise ValueError("EWKB troppo corto per un punto")
    # Primo byte: ordine dei byte (1 = little endian, 0 = big endian).
    order = "<" if raw[0] == 1 else ">"
    (geometry_type,) = struct.unpack(f"{order}I", raw[1:5])
    if geometry_type & 0xFF != _POINT_TYPE:
        raise ValueError("EWKB: non è un punto")
    offset = 5
    if geometry_type & _SRID_FLAG:
        offset += 4  # lo SRID (4326) è qui, ma non ci serve
    dimensions = 2 + bool(geometry_type & _Z_FLAG) + bool(geometry_type & _M_FLAG)
    needed = offset + 8 * dimensions
    if len(raw) < needed:
        raise ValueError("EWKB troncato")
    x, y = struct.unpack(f"{order}dd", raw[offset : offset + 16])
    return (y, x)  # PostGIS: x = longitudine, y = latitudine


def point_from_location(value: Any) -> tuple[float, float] | None:
    """Accetta GeoJSON o EWKB e restituisce `(lat, lng)`; None se non decodificabile."""
    if isinstance(value, dict) and value.get("type") == "Point":
        coords = value.get("coordinates") or []
        try:
            lat, lng = float(coords[1]), float(coords[0])
        except (TypeError, ValueError, IndexError):
            return None
        if not (math.isfinite(lat) and math.isfinite(lng)):
            return None
        return (lat, lng)
    if isinstance(value, str):
        try:
            return parse_ewkb_point(value)
        except ValueError:
            return None
    return None
