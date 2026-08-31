from __future__ import annotations

import re
from typing import Any


# ============================================================
# PATRONES
# ============================================================

# 5%, 0.05%, 0,5 %
CONCENTRATION_PERCENT_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*%",
    flags=re.IGNORECASE,
)

# 20 mg/mL, 2 mg/g, 5 mcg/mL, 1 g/100 mL
CONCENTRATION_RATIO_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*"
    r"(mg|mcg|µg|ug|g)\s*/\s*"
    r"(100\s*)?(m[lL]|g)\b",
    flags=re.IGNORECASE,
)

# 100 ml, 30 g, 500 mg, 0.5 g
QUANTITY_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*"
    r"(mg|mcg|µg|ug|g|kg|ml|mL|l)\b",
    flags=re.IGNORECASE,
)

# cada 8 horas / cada 12 h
FREQUENCY_EVERY_PATTERN = re.compile(
    r"\bcada\s+(\d{1,2})\s*(horas?|hrs?|h)\b",
    flags=re.IGNORECASE,
)

# c/8h / c/12 h
FREQUENCY_SHORT_PATTERN = re.compile(
    r"\bc\s*/\s*(\d{1,2})\s*(h|hr|hrs|horas?)\b",
    flags=re.IGNORECASE,
)

# 2 veces al día / 3 veces por día
FREQUENCY_TIMES_PATTERN = re.compile(
    r"\b(\d+)\s+veces?\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)

# OCR frecuente: 2 vcs day / 2 vcs dia / 2 vces al día
FREQUENCY_OCR_TIMES_PATTERN = re.compile(
    r"\b(\d+)\s*(?:vcs|vces|veces?)\s*(?:al|por)?\s*(?:d[ií]a|day)\b",
    flags=re.IGNORECASE,
)

# una vez al día / una vez por día
FREQUENCY_ONCE_PATTERN = re.compile(
    r"\buna\s+vez\s+(?:al|por)\s+d[ií]a\b",
    flags=re.IGNORECASE,
)

# por 7 días / durante 14 días / x 30 días
DURATION_PATTERN = re.compile(
    r"\b(?:por|durante|x)\s+(\d+)\s*"
    r"(d[ií]as?|semanas?|meses?)\b",
    flags=re.IGNORECASE,
)

# Dosis explícitas: tomar 1 tableta, aplicar 2 mL, administrar 5 gotas
DOSAGE_AMOUNT_PATTERN = re.compile(
    r"\b(?:tomar|aplicar|administrar|usar|ingerir)\s+"
    r"((?:\d+(?:[.,]\d+)?|un|una)\s*"
    r"(?:tabletas?|capsulas?|c[aá]psulas?|gotas?|puffs?|disparos?|"
    r"cucharaditas?|cucharadas?|m[lL]|mg|g))\b",
    flags=re.IGNORECASE,
)

# Dosis tópicas textuales
DOSAGE_TOPICAL_PATTERN = re.compile(
    r"\baplicar\s+(una\s+capa\s+fina|capa\s+fina|cantidad\s+suficiente)\b",
    flags=re.IGNORECASE,
)

# Vías explícitas
ROUTE_PATTERN = re.compile(
    r"\b(?:v[ií]a\s+)?"
    r"(oral|t[oó]pica|cut[aá]nea|sublingual|oft[aá]lmica|[oó]tica|nasal|"
    r"rectal|vaginal|intravenosa|intramuscular|subcut[aá]nea)\b",
    flags=re.IGNORECASE,
)


def _normalize_decimal(value: str) -> str:
    return value.replace(",", ".")


def _normalize_unit(unit: str) -> str:
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


def _overlaps(
    start: int,
    end: int,
    spans: list[tuple[int, int]],
) -> bool:

    return any(
        start < span_end and end > span_start
        for span_start, span_end in spans
    )


# ============================================================
# CONCENTRACIONES
# ============================================================

def extract_concentrations(
    text: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in CONCENTRATION_PERCENT_PATTERN.finditer(text):

        number = _normalize_decimal(
            match.group(1)
        )

        results.append(
            _build_match(
                match,
                "CONCENTRATION",
                f"{number}%",
            )
        )

    for match in CONCENTRATION_RATIO_PATTERN.finditer(text):

        number = _normalize_decimal(
            match.group(1)
        )

        numerator = _normalize_unit(
            match.group(2)
        )

        denominator_prefix = (
            "100 "
            if match.group(3)
            else ""
        )

        denominator = _normalize_unit(
            match.group(4)
        )

        normalized = (
            f"{number} "
            f"{numerator}/"
            f"{denominator_prefix}"
            f"{denominator}"
        )

        results.append(
            _build_match(
                match,
                "CONCENTRATION",
                normalized,
            )
        )

    return sorted(
        results,
        key=lambda item: item["start"],
    )


# ============================================================
# CANTIDADES
# ============================================================

def extract_quantities(
    text: str,
    excluded_spans: list[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    excluded_spans = excluded_spans or []

    for match in QUANTITY_PATTERN.finditer(text):

        if _overlaps(
            match.start(),
            match.end(),
            excluded_spans,
        ):
            continue

        number = _normalize_decimal(
            match.group(1)
        )

        unit = _normalize_unit(
            match.group(2)
        )

        item = _build_match(
            match,
            "QUANTITY",
            f"{number} {unit}",
        )

        item["value"] = float(number)
        item["unit"] = unit

        results.append(item)

    return results


# ============================================================
# FRECUENCIAS
# ============================================================

def extract_frequencies(
    text: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    # cada 8 horas
    for match in FREQUENCY_EVERY_PATTERN.finditer(text):

        hours = int(
            match.group(1)
        )

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                f"cada {hours} horas",
            )
        )

    # c/8h
    for match in FREQUENCY_SHORT_PATTERN.finditer(text):

        hours = int(
            match.group(1)
        )

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                f"cada {hours} horas",
            )
        )

    # 2 veces al día
    # 2 vcs day
    for pattern in (
        FREQUENCY_TIMES_PATTERN,
        FREQUENCY_OCR_TIMES_PATTERN,
    ):

        for match in pattern.finditer(text):

            times = int(
                match.group(1)
            )

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

    # Evitar duplicados.
    unique: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    for result in results:

        unique[
            (
                result["start"],
                result["end"],
            )
        ] = result

    return sorted(
        unique.values(),
        key=lambda item: item["start"],
    )


# ============================================================
# DURACIÓN
# ============================================================

def extract_durations(
    text: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in DURATION_PATTERN.finditer(text):

        value = int(
            match.group(1)
        )

        unit = match.group(2).lower()

        if (
            unit.startswith("día")
            or unit.startswith("dia")
        ):

            unit = (
                "día"
                if value == 1
                else "días"
            )

        elif unit.startswith("semana"):

            unit = (
                "semana"
                if value == 1
                else "semanas"
            )

        elif unit.startswith("mes"):

            unit = (
                "mes"
                if value == 1
                else "meses"
            )

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
# DOSIS
# ============================================================

def extract_dosages(
    text: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for match in DOSAGE_AMOUNT_PATTERN.finditer(text):

        dose = re.sub(
            r"\s+",
            " ",
            match.group(1).strip(),
        )

        dose = re.sub(
            r"\bml\b",
            "mL",
            dose,
            flags=re.IGNORECASE,
        )

        results.append(
            _build_match(
                match,
                "DOSAGE",
                dose,
            )
        )

    for match in DOSAGE_TOPICAL_PATTERN.finditer(text):

        dose = re.sub(
            r"\s+",
            " ",
            match.group(1)
            .strip()
            .lower(),
        )

        results.append(
            _build_match(
                match,
                "DOSAGE",
                dose,
            )
        )

    return sorted(
        results,
        key=lambda item: item["start"],
    )


# ============================================================
# VÍA DE ADMINISTRACIÓN
# ============================================================

def extract_routes(
    text: str,
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    route_map = {
        "topica": "tópica",
        "tópica": "tópica",

        "cutanea": "cutánea",
        "cutánea": "cutánea",

        "oftalmica": "oftálmica",
        "oftálmica": "oftálmica",

        "otica": "ótica",
        "ótica": "ótica",

        "subcutanea": "subcutánea",
        "subcutánea": "subcutánea",
    }

    for match in ROUTE_PATTERN.finditer(text):

        route = (
            match.group(1)
            .lower()
        )

        route = route_map.get(
            route,
            route,
        )

        results.append(
            _build_match(
                match,
                "ROUTE",
                route,
            )
        )

    return results


# ============================================================
# EXTRACTOR PRINCIPAL
# ============================================================

def extract_regex_entities(
    text: str,
) -> dict[str, Any]:

    text = (
        text or ""
    ).strip()

    concentrations = extract_concentrations(
        text
    )

    concentration_spans = [
        (
            item["start"],
            item["end"],
        )
        for item in concentrations
    ]

    quantities = extract_quantities(
        text,
        excluded_spans=concentration_spans,
    )

    frequencies = extract_frequencies(
        text
    )

    durations = extract_durations(
        text
    )

    dosages = extract_dosages(
        text
    )

    routes = extract_routes(
        text
    )

    entities = [
        *concentrations,
        *quantities,
        *dosages,
        *frequencies,
        *durations,
        *routes,
    ]

    entities.sort(
        key=lambda item: item["start"]
    )

    return {

        "concentrations": concentrations,

        "quantities": quantities,

        "dosages": dosages,

        "frequencies": frequencies,

        "durations": durations,

        "routes": routes,

        "entities": entities,
    }