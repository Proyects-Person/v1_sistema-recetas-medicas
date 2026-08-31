from __future__ import annotations

from typing import Any

from ..ocr_dictionary import (
    analyze_ocr_text,
    normalize_for_match,
)

from .regex_extractor import (
    extract_regex_entities,
)


# ============================================================
# CATEGORÍAS DEL DICCIONARIO
# ============================================================

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


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _effective_text(
    original: str,
    dictionary_result: dict[str, Any],
) -> str:

    return (
        dictionary_result.get(
            "normalized_text"
        )
        or original
        or ""
    ).strip()


def _terms_by_category(
    items: list[dict[str, Any]],
    categories: set[str],
) -> list[dict[str, Any]]:

    return [
        item
        for item in items
        if item.get("category")
        in categories
    ]


def _best_term(
    items: list[dict[str, Any]],
    categories: set[str],
) -> dict[str, Any] | None:

    candidates = _terms_by_category(
        items,
        categories,
    )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: float(
            item.get("confidence")
            or 0.0
        ),
    )


def _find_term_span(
    text: str,
    item: dict[str, Any],
) -> tuple[int, int] | None:

    """
    Busca la ubicación aproximada de un medicamento
    o insumo dentro de la línea.

    Primero intenta buscar el nombre canónico y luego
    el texto realmente detectado por OCR/diccionario.
    """

    normalized_text = normalize_for_match(
        text
    )

    for candidate in (
        item.get("term"),
        item.get("match"),
    ):

        candidate_norm = normalize_for_match(
            str(candidate or "")
        )

        if not candidate_norm:
            continue

        start = normalized_text.find(
            candidate_norm
        )

        if start >= 0:

            return (
                start,
                start + len(candidate_norm),
            )

    return None


# ============================================================
# RELACIÓN INSUMO <-> CONCENTRACIÓN
# ============================================================

def _pair_components_with_concentrations(
    line_text: str,
    component_terms: list[dict[str, Any]],
    concentrations: list[dict[str, Any]],
) -> list[
    tuple[
        dict[str, Any],
        dict[str, Any] | None,
    ]
]:

    """
    Relaciona cada medicamento o insumo con su
    concentración correspondiente.

    Ejemplo:

    Oxido de zinc 8% + Calamina 8% + Mentol 0.5%

    Resultado:

    Óxido de zinc -> 8%
    Calamina       -> 8%
    Mentol         -> 0.5%
    """

    if not component_terms:
        return []

    available = set(
        range(len(concentrations))
    )

    positioned: list[
        tuple[
            dict[str, Any],
            tuple[int, int] | None,
        ]
    ] = [

        (
            term,
            _find_term_span(
                line_text,
                term,
            ),
        )

        for term
        in component_terms
    ]

    # Ordenar según posición en el texto.
    positioned.sort(
        key=lambda item:
        item[1][0]
        if item[1]
        else 10**9
    )

    result: list[
        tuple[
            dict[str, Any],
            dict[str, Any] | None,
        ]
    ] = []

    for term, span in positioned:

        chosen_index: int | None = None

        # -----------------------------------------
        # Si conocemos posición del medicamento
        # -----------------------------------------

        if (
            available
            and span is not None
        ):

            _, term_end = span

            # Concentraciones inmediatamente después
            # del medicamento.
            following = [

                idx

                for idx in available

                if (
                    0
                    <= (
                        concentrations[idx]["start"]
                        - term_end
                    )
                    <= 18
                )
            ]

            if following:

                chosen_index = min(
                    following,
                    key=lambda idx:
                    concentrations[idx]["start"]
                    - term_end,
                )

            else:

                # Si no está inmediatamente después,
                # usamos la concentración más cercana.
                term_center = (
                    span[0]
                    + span[1]
                ) / 2

                chosen_index = min(
                    available,
                    key=lambda idx:
                    abs(
                        (
                            (
                                concentrations[idx]["start"]
                                + concentrations[idx]["end"]
                            )
                            / 2
                        )
                        - term_center
                    ),
                )

        # Si solamente queda una concentración disponible,
        # se puede utilizar.
        elif len(available) == 1:

            chosen_index = next(
                iter(available)
            )

        concentration = None

        if chosen_index is not None:

            concentration = concentrations[
                chosen_index
            ]

            available.remove(
                chosen_index
            )

        result.append(
            (
                term,
                concentration,
            )
        )

    return result


# ============================================================
# ELIMINAR COMPONENTES DUPLICADOS
# ============================================================

def _deduplicate_components(
    components: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    """
    Evita repetir el mismo medicamento o insumo.
    """

    by_name: dict[
        str,
        dict[str, Any],
    ] = {}

    for component in components:

        key = normalize_for_match(
            str(
                component.get("name")
                or ""
            )
        )

        if not key:
            continue

        current = by_name.get(
            key
        )

        if current is None:

            by_name[key] = component

            continue

        current_score = (

            1
            if current.get(
                "concentration"
            )
            else 0,

            float(
                current.get(
                    "dictionary_confidence"
                )
                or 0.0
            ),
        )

        candidate_score = (

            1
            if component.get(
                "concentration"
            )
            else 0,

            float(
                component.get(
                    "dictionary_confidence"
                )
                or 0.0
            ),
        )

        if candidate_score > current_score:

            by_name[key] = component

    return list(
        by_name.values()
    )


# ============================================================
# PARSER PRINCIPAL
# ============================================================

def parse_prescription(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    """
    Convierte el texto OCR de la receta médica
    en datos farmacoterapéuticos estructurados.
    """

    original_text = (
        text or ""
    ).strip()

    lines = [

        line.strip()

        for line in original_text.splitlines()

        if line.strip()
    ]

    # ========================================================
    # CAMPOS A EXTRAER
    # ========================================================

    components: list[
        dict[str, Any]
    ] = []

    dosage_form: str | None = None

    total_quantity: dict[
        str,
        Any,
    ] | None = None

    dosage: str | None = None

    frequency: str | None = None

    duration: str | None = None

    administration_route: str | None = None

    unparsed_lines: list[str] = []

    line_analysis: list[
        dict[str, Any]
    ] = []

    # ========================================================
    # ANALIZAR CADA LÍNEA
    # ========================================================

    for (
        line_number,
        original_line,
    ) in enumerate(
        lines,
        start=1,
    ):

        # ----------------------------------------------------
        # DICCIONARIO FARMACÉUTICO
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
        # REGEX
        # ----------------------------------------------------

        matching_text = normalize_for_match(
            line_text
        )

        regex_result = extract_regex_entities(
            matching_text
        )

        concentrations = regex_result[
            "concentrations"
        ]

        quantities = regex_result[
            "quantities"
        ]

        dosages = regex_result[
            "dosages"
        ]

        frequencies = regex_result[
            "frequencies"
        ]

        durations = regex_result[
            "durations"
        ]

        regex_routes = regex_result[
            "routes"
        ]

        # ----------------------------------------------------
        # TÉRMINOS FARMACÉUTICOS
        # ----------------------------------------------------

        component_terms = _terms_by_category(
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

        # ====================================================
        # MEDICAMENTOS / INSUMOS
        # ====================================================

        pairs = _pair_components_with_concentrations(
            matching_text,
            component_terms,
            concentrations,
        )

        for (
            component_term,
            concentration,
        ) in pairs:

            components.append(
                {
                    "name":
                        component_term.get(
                            "term"
                        ),

                    "category":
                        component_term.get(
                            "category"
                        ),

                    "concentration":
                        (
                            concentration.get(
                                "normalized"
                            )
                            if concentration
                            else None
                        ),

                    "dictionary_confidence":
                        component_term.get(
                            "confidence"
                        ),

                    "source_line":
                        original_line,

                    "line_number":
                        line_number,
                }
            )

        # ====================================================
        # FORMA FARMACÉUTICA
        # ====================================================

        if (
            form_term
            and dosage_form is None
        ):

            dosage_form = (
                str(
                    form_term.get(
                        "term"
                    )
                    or ""
                )
                .strip()
                or None
            )

        # ====================================================
        # CANTIDAD TOTAL
        # ====================================================

        if (
            total_quantity is None
            and quantities
        ):

            # Una cantidad se considera presentación/cantidad
            # total principalmente cuando:
            #
            # crema 30 g
            # loción 100 ml
            #
            # o cuando aparece aislada en una línea.
            can_be_total = (

                bool(form_term)

                or (

                    not component_terms

                    and not frequencies

                    and not durations

                    and not dosages
                )
            )

            if can_be_total:

                quantity = quantities[0]

                total_quantity = {

                    "value":
                        quantity.get(
                            "value"
                        ),

                    "unit":
                        quantity.get(
                            "unit"
                        ),

                    "normalized":
                        quantity.get(
                            "normalized"
                        ),

                    "source_line":
                        original_line,
                }

        # ====================================================
        # DOSIS
        # ====================================================

        if (
            dosages
            and dosage is None
        ):

            dosage = dosages[
                0
            ]["normalized"]

        # ====================================================
        # FRECUENCIA
        # ====================================================

        if (
            frequencies
            and frequency is None
        ):

            frequency = frequencies[
                0
            ]["normalized"]

        # ====================================================
        # DURACIÓN
        # ====================================================

        if (
            durations
            and duration is None
        ):

            duration = durations[
                0
            ]["normalized"]

        # ====================================================
        # VÍA DE ADMINISTRACIÓN
        # ====================================================

        if administration_route is None:

            if route_term:

                administration_route = (
                    str(
                        route_term.get(
                            "term"
                        )
                        or ""
                    )
                    .strip()
                    or None
                )

            elif regex_routes:

                administration_route = (
                    regex_routes[
                        0
                    ]["normalized"]
                )

        # ====================================================
        # SABER SI LA LÍNEA FUE ENTENDIDA
        # ====================================================

        understood = any(
            [
                component_terms,
                form_term,
                route_term,
                concentrations,
                quantities,
                dosages,
                frequencies,
                durations,
                regex_routes,
            ]
        )

        if not understood:

            unparsed_lines.append(
                original_line
            )

        # Guardamos análisis interno.
        line_analysis.append(
            {
                "line_number":
                    line_number,

                "original":
                    original_line,

                "normalized":
                    line_text,

                "recognized_terms":
                    recognized,

                "regex":
                    regex_result,
            }
        )

    # ========================================================
    # ELIMINAR REPETICIONES
    # ========================================================

    components = _deduplicate_components(
        components
    )

    # ========================================================
    # CANTIDAD NORMALIZADA
    # ========================================================

    quantity_normalized = (

        total_quantity.get(
            "normalized"
        )

        if total_quantity

        else None
    )

    # ========================================================
    # ESTRUCTURA FINAL ESTÁNDAR
    # ========================================================

    structured_rows = [

        {
            "medication_or_ingredient":
                component.get(
                    "name"
                ),

            "concentration":
                component.get(
                    "concentration"
                ),

            "pharmaceutical_form":
                dosage_form,

            "quantity":
                quantity_normalized,

            "dosage":
                dosage,

            "frequency":
                frequency,

            "duration":
                duration,

            "administration_route":
                administration_route,
        }

        for component in components
    ]

    # ========================================================
    # RESPUESTA DEL PARSER
    # ========================================================

    return {

        "components":
            components,

        "dosage_form":
            dosage_form,

        "total_quantity":
            total_quantity,

        "dosage":
            dosage,

        "frequency":
            frequency,

        "duration":
            duration,

        "administration_route":
            administration_route,

        "structured_rows":
            structured_rows,

        "unparsed_lines":
            unparsed_lines,

        "line_analysis":
            line_analysis,
    }