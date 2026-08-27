from __future__ import annotations

from typing import Any

from ..ocr_dictionary import analyze_ocr_text
from .regex_extractor import extract_regex_entities


# Categorías que ya existen en tu pharmaceutical_terms.json
COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
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
    """
    Usa el texto corregido por diccionario si existe.
    Si el diccionario no hizo cambios, conserva el original.
    """

    return (
        dictionary_result.get("normalized_text")
        or original
        or ""
    ).strip()


def _best_term(
    items: list[dict[str, Any]],
    categories: set[str],
) -> dict[str, Any] | None:
    """
    Obtiene el término reconocido con mayor confianza
    dentro de determinadas categorías.
    """

    candidates = [
        item
        for item in items
        if item.get("category") in categories
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: float(
            item.get("confidence") or 0.0
        ),
    )


def _first_normalized(
    items: list[dict[str, Any]],
) -> str | None:

    if not items:
        return None

    return str(items[0]["normalized"])


def parse_prescription(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Convierte el texto de una receta en una estructura
    farmacéutica preliminar.

    IMPORTANTE:
    El resultado es una sugerencia para posterior
    validación del químico farmacéutico.
    """

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

    # ========================================================
    # ANALIZAMOS LA RECETA LÍNEA POR LÍNEA
    # ========================================================

    for line_number, original_line in enumerate(
        lines,
        start=1,
    ):

        # ----------------------------------------------------
        # 1. Diccionario farmacéutico
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 2. Regex
        # ----------------------------------------------------

        regex_result = extract_regex_entities(
            line_text
        )

        concentrations = regex_result[
            "concentrations"
        ]

        quantities = regex_result[
            "quantities"
        ]

        frequencies = regex_result[
            "frequencies"
        ]

        durations = regex_result[
            "durations"
        ]

        # ----------------------------------------------------
        # 3. Clasificación usando el diccionario
        # ----------------------------------------------------

        component_term = _best_term(
            recognized,
            COMPONENT_CATEGORIES,
        )

        form_term = _best_term(
            recognized,
            FORM_CATEGORIES,
        )

        route_term = _best_term(
            recognized,
            ROUTE_CATEGORIES,
        )

        # ----------------------------------------------------
        # 4. COMPONENTES / INSUMOS
        # ----------------------------------------------------

        if component_term:

            component = {
                "name": component_term["term"],

                "category": component_term.get(
                    "category"
                ),

                "concentration": _first_normalized(
                    concentrations
                ),

                "quantity": (
                    quantities[0]
                    if quantities
                    else None
                ),

                "dictionary_confidence":
                    component_term.get(
                        "confidence"
                    ),

                "source_line": original_line,

                "line_number": line_number,
            }

            components.append(component)

        # ----------------------------------------------------
        # 5. FORMA FARMACÉUTICA
        # ----------------------------------------------------

        if form_term and dosage_form is None:

            dosage_form = str(
                form_term["term"]
            )

        # ----------------------------------------------------
        # 6. CANTIDAD TOTAL DEL PREPARADO
        # ----------------------------------------------------

        if (
            form_term
            and quantities
            and total_quantity is None
        ):

            quantity = quantities[0]

            total_quantity = {
                "value": quantity["value"],
                "unit": quantity["unit"],
                "normalized":
                    quantity["normalized"],
                "source_line":
                    original_line,
            }

        # ----------------------------------------------------
        # 7. FRECUENCIA
        # ----------------------------------------------------

        if frequencies and frequency is None:

            frequency = frequencies[0][
                "normalized"
            ]

        # ----------------------------------------------------
        # 8. DURACIÓN
        # ----------------------------------------------------

        if durations and duration is None:

            duration = durations[0][
                "normalized"
            ]

        # ----------------------------------------------------
        # 9. VÍA DE ADMINISTRACIÓN
        # ----------------------------------------------------

        if (
            route_term
            and administration_route is None
        ):

            administration_route = str(
                route_term["term"]
            )

        # ----------------------------------------------------
        # 10. LÍNEAS QUE TODAVÍA NO ENTENDEMOS
        # ----------------------------------------------------

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

            unparsed_lines.append(
                original_line
            )

        # ----------------------------------------------------
        # Información para auditoría / pruebas
        # ----------------------------------------------------

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
    # JSON FINAL DEL PARSER
    # ========================================================

    return {
        "components": components,
        "dosage_form": dosage_form,
        "total_quantity": total_quantity,
        "frequency": frequency,
        "duration": duration,
        "administration_route":
            administration_route,
        "unparsed_lines": unparsed_lines,
        "line_analysis": line_analysis,
    }