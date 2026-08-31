"""
Extracción estricta de estructuras de receta magistral.

Mejoras basadas en el dataset de 36 recetas:
- Concentraciones porcentuales: 5%, 0.05%, 0,5 %
- Fuerzas en masa: 2.5 mg, 500 mcg
- Grados de alcohol: 90°
- Cantidades totales: 100 mL, 60 cc, 30 g, 30 unidades
- Frecuencia y duración
"""

from __future__ import annotations

import re
from typing import Any


PERCENT_CONCENTRATION_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*%",
    flags=re.IGNORECASE,
)

DEGREE_CONCENTRATION_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*°",
    flags=re.IGNORECASE,
)

# Una fuerza en mg/mcg puede funcionar como concentración/dosis del insumo
# cuando la línea corresponde a un medicamento (ej.: Minoxidil 2.5 mg).
MASS_STRENGTH_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(mg|mcg|µg|ug)\b",
    flags=re.IGNORECASE,
)

QUANTITY_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*"
    r"(mg|mcg|µg|ug|g|kg|ml|mL|cc|l|litros?|unidades?|unidad)\b",
    flags=re.IGNORECASE,
)

FREQUENCY_EVERY_PATTERN = re.compile(
    r"\bcada\s+(\d{1,2})\s*(horas?|hrs?|h)\b",
    flags=re.IGNORECASE,
)

FREQUENCY_SHORT_PATTERN = re.compile(
    r"\bc\s*/\s*(\d{1,2})\s*(h|hr|hrs|horas?)\b",
    flags=re.IGNORECASE,
)

FREQUENCY_TIMES_PATTERN = re.compile(
    r"\b(\d+)\s+veces?\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)

FREQUENCY_ONCE_PATTERN = re.compile(
    r"\buna\s+vez\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    r"\b(?:por|durante|x)\s+(\d+)\s*"
    r"(d[ií]as?|semanas?|meses?)\b",
    flags=re.IGNORECASE,
)


def _normalize_decimal(value: str) -> str:
    return value.replace(",", ".")


def _normalize_unit(unit: str) -> str:
    normalized = unit.lower().strip()
    aliases = {
        "ml": "mL",
        "cc": "mL",
        "l": "L",
        "litro": "L",
        "litros": "L",
        "ug": "mcg",
        "µg": "mcg",
        "unidades": "unidad",
    }
    return aliases.get(normalized, normalized)


def _build_match(
    match: re.Match,
    entity_type: str,
    normalized_value: str | None = None,
) -> dict[str, Any]:
    return {
        "type": entity_type,
        "text": match.group(0).strip(),
        "normalized": normalized_value or match.group(0).strip(),
        "start": match.start(),
        "end": match.end(),
    }


def extract_concentrations(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for match in PERCENT_CONCENTRATION_PATTERN.finditer(text):
        number = _normalize_decimal(match.group(1))
        item = _build_match(match, "CONCENTRATION", f"{number}%")
        item["value"] = float(number)
        item["unit"] = "%"
        results.append(item)

    for match in DEGREE_CONCENTRATION_PATTERN.finditer(text):
        number = _normalize_decimal(match.group(1))
        item = _build_match(match, "CONCENTRATION", f"{number}°")
        item["value"] = float(number)
        item["unit"] = "°"
        results.append(item)

    # Las fuerzas mg/mcg se agregan como concentración estructural.
    for match in MASS_STRENGTH_PATTERN.finditer(text):
        number = _normalize_decimal(match.group(1))
        unit = _normalize_unit(match.group(2))
        item = _build_match(match, "CONCENTRATION", f"{number} {unit}")
        item["value"] = float(number)
        item["unit"] = unit
        results.append(item)

    # Evitar solapamientos exactos por posición.
    unique: dict[tuple[int, int], dict[str, Any]] = {}
    for item in results:
        unique[(item["start"], item["end"])] = item
    return sorted(unique.values(), key=lambda item: item["start"])


def extract_quantities(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for match in QUANTITY_PATTERN.finditer(text):
        number = _normalize_decimal(match.group(1))
        unit = _normalize_unit(match.group(2))
        item = _build_match(match, "QUANTITY", f"{number} {unit}")
        item["value"] = float(number)
        item["unit"] = unit
        results.append(item)

    return results


def extract_frequencies(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for match in FREQUENCY_EVERY_PATTERN.finditer(text):
        hours = int(match.group(1))
        results.append(_build_match(match, "FREQUENCY", f"cada {hours} horas"))

    for match in FREQUENCY_SHORT_PATTERN.finditer(text):
        hours = int(match.group(1))
        results.append(_build_match(match, "FREQUENCY", f"cada {hours} horas"))

    for match in FREQUENCY_TIMES_PATTERN.finditer(text):
        times = int(match.group(1))
        results.append(_build_match(match, "FREQUENCY", f"{times} veces al día"))

    for match in FREQUENCY_ONCE_PATTERN.finditer(text):
        results.append(_build_match(match, "FREQUENCY", "1 vez al día"))

    unique: dict[tuple[int, int], dict[str, Any]] = {}
    for result in results:
        unique[(result["start"], result["end"])] = result

    return sorted(unique.values(), key=lambda item: item["start"])


def extract_durations(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for match in DURATION_PATTERN.finditer(text):
        value = int(match.group(1))
        unit = match.group(2).lower()

        if unit.startswith("día") or unit.startswith("dia"):
            unit = "día" if value == 1 else "días"
        elif unit.startswith("semana"):
            unit = "semana" if value == 1 else "semanas"
        elif unit.startswith("mes"):
            unit = "mes" if value == 1 else "meses"

        item = _build_match(match, "DURATION", f"{value} {unit}")
        item["value"] = value
        item["unit"] = unit
        results.append(item)

    return results


def extract_regex_entities(text: str) -> dict[str, Any]:
    text = (text or "").strip()

    concentrations = extract_concentrations(text)
    quantities = extract_quantities(text)
    frequencies = extract_frequencies(text)
    durations = extract_durations(text)

    entities = [
        *concentrations,
        *quantities,
        *frequencies,
        *durations,
    ]
    entities.sort(key=lambda item: (item["start"], item["end"], item["type"]))

    return {
        "concentrations": concentrations,
        "quantities": quantities,
        "frequencies": frequencies,
        "durations": durations,
        "entities": entities,
    }
