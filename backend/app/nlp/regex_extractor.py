"""
Extracción estricta de datos cuantitativos
en recetas médicas.

IMPORTANTE:

Este módulo NO decide qué palabra es un medicamento.

Su responsabilidad es reconocer únicamente
estructuras numéricas farmacológicamente válidas:

- 5%
- 0.05%
- 2,5%
- 2.5 mg
- 500 mcg
- 90°
- 100 mL
- 30 g
- frecuencia
- duración

La salida final INSUMO + CONCENTRACIÓN
se decide posteriormente en entity_fusion.py.
"""

from __future__ import annotations

import re

from typing import Any


# ============================================================
# PORCENTAJES
#
# Soporta:
#
# 5%
# 0.05%
# 0,05%
# Urea5%
# Clobetasol0,05%
# ============================================================

PERCENT_CONCENTRATION_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*%",
    flags=re.IGNORECASE,
)


# ============================================================
# GRADOS
#
# Ejemplo:
#
# Alcohol 90°
# ============================================================

DEGREE_CONCENTRATION_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*°",
    flags=re.IGNORECASE,
)


# ============================================================
# FUERZA EN MASA
#
# Ejemplos:
#
# Minoxidil 2.5 mg
# Minoxidil2,5mg
# ============================================================

MASS_STRENGTH_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*"
    r"(mg|mcg|µg|ug)"
    r"\b",
    flags=re.IGNORECASE,
)


# ============================================================
# CONCENTRACIONES COMPUESTAS
#
# Ejemplos futuros:
#
# 10 mg/mL
# 5 mg/g
# ============================================================

RATIO_STRENGTH_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*"
    r"(mg|mcg|µg|ug)"
    r"\s*/\s*"
    r"(ml|mL|g)"
    r"\b",
    flags=re.IGNORECASE,
)


# ============================================================
# CANTIDADES DEL PREPARADO
#
# ATENCIÓN:
#
# 120 g
# 60 mL
# 30 cápsulas
#
# son CANTIDADES,
# NO concentraciones.
# ============================================================

QUANTITY_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d+(?:[.,]\d+)?)"
    r"\s*"
    r"("
    r"g|kg|"
    r"ml|mL|cc|l|litros?|"
    r"unidades?|unidad|"
    r"c[aá]psulas?|"
    r"tabletas?|tabs?|"
    r"tubos?|tub\.?|"
    r"frascos?"
    r")"
    r"\b",
    flags=re.IGNORECASE,
)


# ============================================================
# FRECUENCIA
# ============================================================

FREQUENCY_EVERY_PATTERN = re.compile(
    r"\bcada\s+"
    r"(\d{1,2})\s*"
    r"(horas?|hrs?|h)"
    r"\b",
    flags=re.IGNORECASE,
)


FREQUENCY_SHORT_PATTERN = re.compile(
    r"\bc\s*/\s*"
    r"(\d{1,2})\s*"
    r"(h|hr|hrs|horas?)"
    r"\b",
    flags=re.IGNORECASE,
)


FREQUENCY_TIMES_PATTERN = re.compile(
    r"\b(\d+)\s+"
    r"veces?\s+"
    r"(?:al|por)\s+"
    r"d[ií]a\b",
    flags=re.IGNORECASE,
)


FREQUENCY_ONCE_PATTERN = re.compile(
    r"\b(?:una|1)\s+vez\s+"
    r"(?:al|por)\s+"
    r"d[ií]a\b",
    flags=re.IGNORECASE,
)


# ============================================================
# DURACIÓN
# ============================================================

DURATION_PATTERN = re.compile(
    r"\b(?:por|durante|x)\s+"
    r"(\d+)\s*"
    r"(d[ií]as?|semanas?|meses?)"
    r"\b",
    flags=re.IGNORECASE,
)


# ============================================================
# NORMALIZAR DECIMALES
# ============================================================

def _normalize_decimal(
    value: str,
) -> str:

    return value.replace(
        ",",
        "."
    )


# ============================================================
# NORMALIZAR UNIDADES
# ============================================================

def _normalize_unit(
    unit: str,
) -> str:

    normalized = (
        unit
        .lower()
        .strip()
        .rstrip(".")
    )

    aliases = {

        "ml":
            "mL",

        "cc":
            "mL",

        "l":
            "L",

        "litro":
            "L",

        "litros":
            "L",

        "ug":
            "mcg",

        "µg":
            "mcg",

        "unidades":
            "unidad",

        "capsula":
            "cápsula",

        "capsulas":
            "cápsula",

        "cápsula":
            "cápsula",

        "cápsulas":
            "cápsula",

        "tableta":
            "tableta",

        "tabletas":
            "tableta",

        "tab":
            "tableta",

        "tabs":
            "tableta",

        "tubo":
            "tubo",

        "tubos":
            "tubo",

        "tub":
            "tubo",

        "frasco":
            "frasco",

        "frascos":
            "frasco",
    }

    return aliases.get(
        normalized,
        normalized
    )


# ============================================================
# CONSTRUIR RESULTADO
# ============================================================

def _build_match(
    match: re.Match,
    entity_type: str,
    normalized_value: str | None = None,
) -> dict[str, Any]:

    return {

        "type":
            entity_type,

        "text":
            match.group(0).strip(),

        "normalized":
            (
                normalized_value
                or match.group(0).strip()
            ),

        "start":
            match.start(),

        "end":
            match.end(),
    }


# ============================================================
# EXTRAER CONCENTRACIONES
# ============================================================

def extract_concentrations(
    text: str,
) -> list[
    dict[str, Any]
]:

    results: list[
        dict[str, Any]
    ] = []


    # --------------------------------------------------------
    # CONCENTRACIONES COMPUESTAS PRIMERO
    # --------------------------------------------------------

    ratio_spans: set[
        tuple[int, int]
    ] = set()


    for match in (
        RATIO_STRENGTH_PATTERN
        .finditer(text)
    ):

        number = _normalize_decimal(
            match.group(1)
        )

        numerator = _normalize_unit(
            match.group(2)
        )

        denominator = _normalize_unit(
            match.group(3)
        )

        normalized = (
            f"{number} "
            f"{numerator}/{denominator}"
        )

        item = _build_match(
            match,
            "CONCENTRATION",
            normalized,
        )

        item["value"] = float(
            number
        )

        item["unit"] = (
            f"{numerator}/{denominator}"
        )

        results.append(
            item
        )

        ratio_spans.add(
            (
                match.start(),
                match.end(),
            )
        )


    # --------------------------------------------------------
    # PORCENTAJES
    # --------------------------------------------------------

    for match in (
        PERCENT_CONCENTRATION_PATTERN
        .finditer(text)
    ):

        number = _normalize_decimal(
            match.group(1)
        )

        item = _build_match(
            match,
            "CONCENTRATION",
            f"{number}%",
        )

        item["value"] = float(
            number
        )

        item["unit"] = "%"

        results.append(
            item
        )


    # --------------------------------------------------------
    # GRADOS
    # --------------------------------------------------------

    for match in (
        DEGREE_CONCENTRATION_PATTERN
        .finditer(text)
    ):

        number = _normalize_decimal(
            match.group(1)
        )

        item = _build_match(
            match,
            "CONCENTRATION",
            f"{number}°",
        )

        item["value"] = float(
            number
        )

        item["unit"] = "°"

        results.append(
            item
        )


    # --------------------------------------------------------
    # mg / mcg
    # --------------------------------------------------------

    for match in (
        MASS_STRENGTH_PATTERN
        .finditer(text)
    ):

        # Evitar duplicar un valor que ya forma
        # parte de algo como 10 mg/mL.
        inside_ratio = any(
            (
                match.start() >= start
                and match.end() <= end
            )
            for start, end
            in ratio_spans
        )

        if inside_ratio:
            continue


        number = _normalize_decimal(
            match.group(1)
        )

        unit = _normalize_unit(
            match.group(2)
        )

        item = _build_match(
            match,
            "CONCENTRATION",
            f"{number} {unit}",
        )

        item["value"] = float(
            number
        )

        item["unit"] = unit

        results.append(
            item
        )


    # --------------------------------------------------------
    # DEDUPLICAR
    # --------------------------------------------------------

    unique: dict[
        tuple[
            int,
            int,
            str,
        ],
        dict[str, Any],
    ] = {}


    for item in results:

        key = (
            int(
                item["start"]
            ),
            int(
                item["end"]
            ),
            str(
                item["normalized"]
            ),
        )

        unique[key] = item


    return sorted(
        unique.values(),
        key=lambda item: (
            item["start"],
            item["end"],
        )
    )


# ============================================================
# EXTRAER CANTIDADES
# ============================================================

def extract_quantities(
    text: str,
) -> list[
    dict[str, Any]
]:

    results: list[
        dict[str, Any]
    ] = []


    for match in (
        QUANTITY_PATTERN
        .finditer(text)
    ):

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

        item["value"] = float(
            number
        )

        item["unit"] = unit

        results.append(
            item
        )


    return results


# ============================================================
# EXTRAER FRECUENCIA
# ============================================================

def extract_frequencies(
    text: str,
) -> list[
    dict[str, Any]
]:

    results: list[
        dict[str, Any]
    ] = []


    for match in (
        FREQUENCY_EVERY_PATTERN
        .finditer(text)
    ):

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


    for match in (
        FREQUENCY_SHORT_PATTERN
        .finditer(text)
    ):

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


    for match in (
        FREQUENCY_TIMES_PATTERN
        .finditer(text)
    ):

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


    for match in (
        FREQUENCY_ONCE_PATTERN
        .finditer(text)
    ):

        results.append(
            _build_match(
                match,
                "FREQUENCY",
                "1 vez al día",
            )
        )


    unique: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}


    for item in results:

        unique[
            (
                item["start"],
                item["end"],
            )
        ] = item


    return sorted(
        unique.values(),
        key=lambda item:
            item["start"]
    )


# ============================================================
# EXTRAER DURACIONES
# ============================================================

def extract_durations(
    text: str,
) -> list[
    dict[str, Any]
]:

    results: list[
        dict[str, Any]
    ] = []


    for match in (
        DURATION_PATTERN
        .finditer(text)
    ):

        value = int(
            match.group(1)
        )

        unit = (
            match
            .group(2)
            .lower()
        )


        if (
            unit.startswith(
                "día"
            )
            or unit.startswith(
                "dia"
            )
        ):

            unit = (
                "día"
                if value == 1
                else "días"
            )


        elif unit.startswith(
            "semana"
        ):

            unit = (
                "semana"
                if value == 1
                else "semanas"
            )


        elif unit.startswith(
            "mes"
        ):

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

        results.append(
            item
        )


    return results


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def extract_regex_entities(
    text: str,
) -> dict[str, Any]:

    text = (
        text
        or ""
    ).strip()


    concentrations = (
        extract_concentrations(
            text
        )
    )


    quantities = (
        extract_quantities(
            text
        )
    )


    frequencies = (
        extract_frequencies(
            text
        )
    )


    durations = (
        extract_durations(
            text
        )
    )


    entities = [
        *concentrations,
        *quantities,
        *frequencies,
        *durations,
    ]


    entities.sort(
        key=lambda item: (
            item["start"],
            item["end"],
            item["type"],
        )
    )


    return {

        "concentrations":
            concentrations,

        "quantities":
            quantities,

        "frequencies":
            frequencies,

        "durations":
            durations,

        "entities":
            entities,
    }