
"""
La responsabilidad de este codigo sera detectar estructuras muy claras.
como por ejemplo:
Oxifo de zinc 8%
Calamina 8%
La idea es que este codigo sea muy estricto y no detecte cosas que no sean claras.
Otro ejemplo:

Aplicar cada 8 horas por 7 días

obtendrá:

cada 8 horas → FREQUENCY
7 días       → DURATION
"""


from __future__ import annotations

import re
from typing import Any


# ============================================================
# PATRONES
# ============================================================

# Ejemplos:
# 5%
# 0.05%
# 0,5 %
CONCENTRATION_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*%",
    flags=re.IGNORECASE,
)


# Ejemplos:
# 100 ml
# 30 g
# 500 mg
# 0.5 g
QUANTITY_PATTERN = re.compile(
    r"(?<!\w)(\d+(?:[.,]\d+)?)\s*"
    r"(mg|mcg|µg|ug|g|kg|ml|mL|l)\b",
    flags=re.IGNORECASE,
)


# Ejemplos:
# cada 8 horas
# cada 12 h
FREQUENCY_EVERY_PATTERN = re.compile(
    r"\bcada\s+(\d{1,2})\s*(horas?|hrs?|h)\b",
    flags=re.IGNORECASE,
)


# Ejemplos:
# c/8h
# c/12 h
FREQUENCY_SHORT_PATTERN = re.compile(
    r"\bc\s*/\s*(\d{1,2})\s*(h|hr|hrs|horas?)\b",
    flags=re.IGNORECASE,
)


# Ejemplos:
# 2 veces al día
# 3 veces por día
FREQUENCY_TIMES_PATTERN = re.compile(
    r"\b(\d+)\s+veces?\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)


# Ejemplos:
# una vez al día
# una vez por día
FREQUENCY_ONCE_PATTERN = re.compile(
    r"\buna\s+vez\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)


# Ejemplos:
# por 7 días
# durante 14 días
# x 30 días
DURATION_PATTERN = re.compile(
    r"\b(?:por|durante|x)\s+(\d+)\s*"
    r"(d[ií]as?|semanas?|meses?)\b",
    flags=re.IGNORECASE,
)


def _normalize_decimal(value: str) -> str:
    """
    Convierte coma decimal a punto.
    Ejemplo:
        0,5 -> 0.5
    """
    return value.replace(",", ".")


def _normalize_unit(unit: str) -> str:
    """
    Normaliza unidades para obtener una salida consistente.
    """

    normalized = unit.lower().strip()

    aliases = {
        "ml": "mL",
        "l": "L",
        "ug": "mcg",
        "µg": "mcg",
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


# ============================================================
# EXTRACTORES
# ============================================================

def extract_concentrations(text: str) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in CONCENTRATION_PATTERN.finditer(text):

        number = _normalize_decimal(match.group(1))

        results.append(
            _build_match(
                match,
                "CONCENTRATION",
                f"{number}%",
            )
        )

    return results


def extract_quantities(text: str) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in QUANTITY_PATTERN.finditer(text):

        number = _normalize_decimal(match.group(1))
        unit = _normalize_unit(match.group(2))

        item = _build_match(
            match,
            "QUANTITY",
            f"{number} {unit}",
        )

        item["value"] = float(number)
        item["unit"] = unit

        results.append(item)

    return results


def extract_frequencies(text: str) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    # cada 8 horas
    for match in FREQUENCY_EVERY_PATTERN.finditer(text):

        hours = int(match.group(1))

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                f"cada {hours} horas",
            )
        )

    # c/8h
    for match in FREQUENCY_SHORT_PATTERN.finditer(text):

        hours = int(match.group(1))

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                f"cada {hours} horas",
            )
        )

    # 2 veces al día
    for match in FREQUENCY_TIMES_PATTERN.finditer(text):

        times = int(match.group(1))

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                f"{times} veces al día",
            )
        )

    # una vez al día
    for match in FREQUENCY_ONCE_PATTERN.finditer(text):

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                "1 vez al día",
            )
        )

    # Evitar duplicados por posición.
    unique: dict[tuple[int, int], dict[str, Any]] = {}

    for result in results:
        unique[(result["start"], result["end"])] = result

    return sorted(
        unique.values(),
        key=lambda item: item["start"],
    )


def extract_durations(text: str) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in DURATION_PATTERN.finditer(text):

        value = int(match.group(1))
        unit = match.group(2).lower()

        # Normalización de tildes y plurales.
        if unit.startswith("día") or unit.startswith("dia"):
            unit = "día" if value == 1 else "días"

        elif unit.startswith("semana"):
            unit = "semana" if value == 1 else "semanas"

        elif unit.startswith("mes"):
            unit = "mes" if value == 1 else "meses"

        item = _build_match(
            match,
            "DURATION",
            f"{value} {unit}",
        )

        item["value"] = value
        item["unit"] = unit

        results.append(item)

    return results


# ============================================================
# EXTRACTOR PRINCIPAL
# ============================================================

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

    entities.sort(
        key=lambda item: item["start"]
    )

    return {
        "concentrations": concentrations,
        "quantities": quantities,
        "frequencies": frequencies,
        "durations": durations,
        "entities": entities,
    }