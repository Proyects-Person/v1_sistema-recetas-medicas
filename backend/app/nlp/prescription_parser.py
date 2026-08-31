from __future__ import annotations

from typing import Any

from ..ocr_dictionary import analyze_ocr_text
from .regex_extractor import extract_regex_entities


# Componentes que pueden formar parte de una fórmula magistral.
COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}

FORM_CATEGORIES = {
    "forma_farmaceutica",
    "forma_base",
}

ROUTE_CATEGORIES = {
    "via",
    "via_administracion",
}


def _effective_text(
    original: str,
    dictionary_result: dict[str, Any],
) -> str:
    return (
        dictionary_result.get("normalized_text")
        or original
        or ""
    ).strip()


def _best_term(
    items: list[dict[str, Any]],
    categories: set[str],
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if item.get("category") in categories
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: float(item.get("confidence") or 0.0),
    )


def _best_form_term(
    items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Prefiere una forma farmacéutica explícita (Gel, Crema, Loción, etc.)
    frente a una forma_base (gel base, crema base) cuando ambas coinciden.
    """
    candidates = [
        item
        for item in items
        if item.get("category") in FORM_CATEGORIES
    ]
    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            float(item.get("confidence") or 0.0),
            1 if item.get("category") == "forma_farmaceutica" else 0,
        ),
    )


def _first_normalized(
    items: list[dict[str, Any]],
) -> str | None:
    if not items:
        return None
    return str(items[0]["normalized"])


def _non_overlapping_quantities(
    concentrations: list[dict[str, Any]],
    quantities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Evita guardar dos veces una fuerza en mg/mcg.

    Ejemplo:
        Minoxidil 2.5 mg

    El regex la puede detectar como CONCENTRATION y QUANTITY.
    Para el componente se conserva como concentración/fuerza.
    """
    concentration_spans = {
        (item["start"], item["end"])
        for item in concentrations
    }
    return [
        item
        for item in quantities
        if (item["start"], item["end"]) not in concentration_spans
    ]


def parse_prescription(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    original_text = (text or "").strip()

    lines = [
        line.strip()
        for line in original_text.splitlines()
        if line.strip()
    ]

    components: list[dict[str, Any]] = []

    dosage_form: str | None = None
    total_quantity: dict[str, Any] | None = None
    frequency: str | None = None
    duration: str | None = None
    administration_route: str | None = None

    unparsed_lines: list[str] = []
    line_analysis: list[dict[str, Any]] = []

    for line_number, original_line in enumerate(lines, start=1):

        dictionary_result = analyze_ocr_text(
            original_line,
            ocr_confidence,
        )

        line_text = _effective_text(
            original_line,
            dictionary_result,
        )

        recognized = dictionary_result.get(
            "recognized_terms",
            [],
        )

        regex_result = extract_regex_entities(line_text)

        concentrations = regex_result["concentrations"]
        quantities = regex_result["quantities"]
        frequencies = regex_result["frequencies"]
        durations = regex_result["durations"]

        component_term = _best_term(
            recognized,
            COMPONENT_CATEGORIES,
        )
        form_term = _best_form_term(recognized)
        route_term = _best_term(
            recognized,
            ROUTE_CATEGORIES,
        )

        # ----------------------------------------------------
        # COMPONENTE / INSUMO
        # ----------------------------------------------------
        if component_term:
            usable_quantities = _non_overlapping_quantities(
                concentrations,
                quantities,
            )

            component = {
                "name": component_term["term"],
                "category": component_term.get("category"),
                "concentration": _first_normalized(concentrations),
                "quantity": (
                    usable_quantities[0]
                    if usable_quantities
                    else None
                ),
                "dictionary_confidence": component_term.get("confidence"),
                "source_line": original_line,
                "line_number": line_number,
            }

            components.append(component)

        # ----------------------------------------------------
        # FORMA FARMACÉUTICA
        # ----------------------------------------------------
        if form_term and dosage_form is None:
            dosage_form = str(form_term["term"])

        # ----------------------------------------------------
        # CANTIDAD TOTAL
        # Solo una línea reconocida como forma farmacéutica
        # puede definir la cantidad total del preparado.
        # ----------------------------------------------------
        if form_term and quantities and total_quantity is None:
            quantity = quantities[0]
            total_quantity = {
                "value": quantity["value"],
                "unit": quantity["unit"],
                "normalized": quantity["normalized"],
                "source_line": original_line,
            }

        if frequencies and frequency is None:
            frequency = frequencies[0]["normalized"]

        if durations and duration is None:
            duration = durations[0]["normalized"]

        if route_term and administration_route is None:
            administration_route = str(route_term["term"])

        understood = any(
            [
                component_term,
                form_term,
                route_term,
                concentrations,
                quantities,
                frequencies,
                durations,
            ]
        )

        if not understood:
            unparsed_lines.append(original_line)

        line_analysis.append(
            {
                "line_number": line_number,
                "original": original_line,
                "normalized": line_text,
                "recognized_terms": recognized,
                "regex": regex_result,
            }
        )

    # ========================================================
    # SALIDA ESTRUCTURADA PARA API / FRONTEND
    # ========================================================
    quantity_normalized = (
        total_quantity.get("normalized")
        if total_quantity
        else None
    )

    structured_rows = [
        {
            "medication_or_ingredient": component.get("name"),
            "concentration": component.get("concentration"),
            "pharmaceutical_form": dosage_form,
            "quantity": quantity_normalized,
            "dosage": None,
            "frequency": frequency,
            "duration": duration,
            "administration_route": administration_route,
        }
        for component in components
    ]

    return {
        "components": components,
        "dosage_form": dosage_form,
        "total_quantity": total_quantity,
        "dosage": None,
        "frequency": frequency,
        "duration": duration,
        "administration_route": administration_route,
        "structured_rows": structured_rows,
        "unparsed_lines": unparsed_lines,
        "line_analysis": line_analysis,
    }
