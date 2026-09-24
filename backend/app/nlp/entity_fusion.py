from __future__ import annotations

import re
import unicodedata

from dataclasses import (
    dataclass,
    field,
)

from typing import Any


from ..ocr_dictionary import (
    analyze_ocr_text,
)

from .ner_extractor import (
    extract_ner_entities,
)

from .regex_extractor import (
    extract_regex_entities,
)


# ============================================================
# CATEGORÍAS QUE PUEDEN SER INSUMOS
# ============================================================

COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}


BASE_CATEGORIES = {
    "base",
    "base_o_excipiente",
}


# ============================================================
# CONTEXTO ADMINISTRATIVO
#
# Estas líneas no deben generar ingredientes aunque
# el NER se equivoque.
#
# Rp. NO se incluye porque puede contener medicamentos.
# ============================================================

ADMIN_PATTERN = re.compile(
    r"(?:"
    r"policlinico|"
    r"nueva\s+esperanza|"
    r"teresalud|"
    r"e\s*\.?\s*i\s*\.?\s*r\s*\.?\s*l\s*\.?|"
    r"huaral|"
    r"av\s*\.?\s+solar|"
    r"avenida|"
    r"direccion|"
    r"www\s*\.|"
    r"@|"
    r"e\s*mail|"
    r"correo|"
    r"telefono|"
    r"celular|"
    r"\bcmp\b|"
    r"\brne\b|"
    r"\bruc\b|"
    r"medico|"
    r"cirujano|"
    r"dermatologo|"
    r"nombres?\s+y\s+apellidos?|"
    r"proxima\s+cita|"
    r"visitanos\s+en|"
    r"central\s*:|"
    r"lider\s+en"
    r")",
    flags=re.IGNORECASE,
)


# ============================================================
# ENCABEZADOS QUE NO SON INGREDIENTES
# ============================================================

SECTION_HEADER_PATTERN = re.compile(
    r"^\s*(?:"
    r"dx\.?|"
    r"diagnostico\s*:?\s*|"
    r"limpieza\s*:?\s*|"
    r"hidratacion\s*:?\s*|"
    r"indicaciones?\s*:?\s*|"
    r"fecha\s*:?\s*|"
    r"proxima\s+cita\s*:?\s*"
    r")$",
    flags=re.IGNORECASE,
)


# ============================================================
# C.S.P.
# ============================================================

CSP_PATTERN = re.compile(
    r"\b(?:"
    r"c\s*\.?\s*s\s*\.?\s*p\s*\.?"
    r"|csp"
    r"|c\s*/\s*p"
    r")\b",
    flags=re.IGNORECASE,
)


# ============================================================
# CANDIDATO
# ============================================================

@dataclass
class Candidate:

    name: str

    start: int

    end: int

    category: str | None = None

    dictionary_confidence: float = 0.0

    dictionary_mode: str | None = None

    statistical_ner: bool = False

    dictionary_ruler: bool = False

    concentration: str | None = None

    sources: set[str] = field(
        default_factory=set
    )


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _strip_accents(
    value: str,
) -> str:

    normalized = (
        unicodedata.normalize(
            "NFD",
            value,
        )
    )

    return "".join(
        character
        for character in normalized
        if unicodedata.category(
            character
        )
        != "Mn"
    )


def _simple_norm(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        _strip_accents(
            (
                value
                or ""
            ).casefold()
        ),
    ).strip()


# ============================================================
# LÍNEA ADMINISTRATIVA
# ============================================================

def _is_administrative(
    line: str,
) -> bool:

    normalized = (
        _simple_norm(
            line
        )
    )

    return bool(
        ADMIN_PATTERN.search(
            normalized
        )
    )


def _is_section_header(
    line: str,
) -> bool:

    normalized = (
        _simple_norm(
            line
        )
    )

    return bool(
        SECTION_HEADER_PATTERN.fullmatch(
            normalized
        )
    )


# ============================================================
# BUSCAR TÉRMINO EN LÍNEA
# ============================================================

def _find_span(
    line: str,
    value: str,
) -> tuple[int, int] | None:

    if not value:
        return None


    # --------------------------------------------------------
    # INTENTO LITERAL
    # --------------------------------------------------------

    match = re.search(
        re.escape(
            value
        ),
        line,
        flags=re.IGNORECASE,
    )

    if match:

        return (
            match.start(),
            match.end(),
        )


    # --------------------------------------------------------
    # INTENTO IGNORANDO TILDES
    # --------------------------------------------------------

    normalized_line = (
        _strip_accents(
            line.casefold()
        )
    )

    normalized_value = (
        _strip_accents(
            value.casefold()
        )
    )


    index = (
        normalized_line.find(
            normalized_value
        )
    )


    if index >= 0:

        return (
            index,
            index + len(value),
        )


    return None


# ============================================================
# LÍNEAS + OFFSETS
# ============================================================

def _line_spans(
    text: str,
) -> list[
    tuple[
        int,
        int,
        str,
    ]
]:

    spans = []


    for match in re.finditer(
        r"[^\r\n]+",
        text,
    ):

        raw = (
            match.group(0)
        )

        clean = (
            raw.strip()
        )


        if not clean:
            continue


        leading = (
            len(raw)
            - len(
                raw.lstrip()
            )
        )


        start = (
            match.start()
            + leading
        )


        end = (
            start
            + len(clean)
        )


        spans.append(
            (
                start,
                end,
                clean,
            )
        )


    return spans


# ============================================================
# ENTIDADES NER DE UNA LÍNEA
# ============================================================

def _entities_for_line(
    entities: list[
        dict[str, Any]
    ],
    line_start: int,
    line_end: int,
) -> list[
    dict[str, Any]
]:

    result = []


    for entity in entities:

        if (
            entity["start"]
            < line_end

            and entity["end"]
            > line_start
        ):

            copy = dict(
                entity
            )


            copy[
                "line_start"
            ] = max(
                0,
                int(
                    entity["start"]
                )
                - line_start,
            )


            copy[
                "line_end"
            ] = max(
                0,
                int(
                    entity["end"]
                )
                - line_start,
            )


            result.append(
                copy
            )


    return result


# ============================================================
# FUSIONAR CANDIDATOS
# ============================================================

def _merge_candidates(
    candidates: list[
        Candidate
    ],
) -> list[
    Candidate
]:

    merged: list[
        Candidate
    ] = []


    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.start,
            item.end,
        ),
    ):

        target: Candidate | None = None


        for existing in merged:

            overlaps = (
                candidate.start
                < existing.end

                and candidate.end
                > existing.start
            )


            same_name = (
                _simple_norm(
                    candidate.name
                )
                ==
                _simple_norm(
                    existing.name
                )
            )


            if (
                overlaps
                or same_name
            ):

                target = (
                    existing
                )

                break


        if target is None:

            merged.append(
                candidate
            )

            continue


        # ----------------------------------------------------
        # DAR PRIORIDAD AL DICCIONARIO
        # ----------------------------------------------------

        if (
            candidate.dictionary_confidence
            > target.dictionary_confidence
        ):

            target.name = (
                candidate.name
            )

            target.start = (
                candidate.start
            )

            target.end = (
                candidate.end
            )

            target.category = (
                candidate.category
            )

            target.dictionary_confidence = (
                candidate.dictionary_confidence
            )

            target.dictionary_mode = (
                candidate.dictionary_mode
            )


        if (
            not target.category
            and candidate.category
        ):

            target.category = (
                candidate.category
            )


        target.statistical_ner = (
            target.statistical_ner
            or candidate.statistical_ner
        )


        target.dictionary_ruler = (
            target.dictionary_ruler
            or candidate.dictionary_ruler
        )


        target.sources.update(
            candidate.sources
        )


    return merged


# ============================================================
# EMPAREJAR INSUMO + CONCENTRACIÓN
#
# IMPORTANTE:
# SOLO UTILIZA CONCENTRACIONES DEL REGEX.
#
# No utiliza CONCENTRACION del NER.
#
# De esta manera:
#
# E.I.R.L
# N°
#
# nunca pueden convertirse en concentración.
# ============================================================

def _pair_concentrations(
    candidates: list[
        Candidate
    ],
    concentrations: list[
        dict[str, Any]
    ],
) -> None:

    if (
        not candidates
        or not concentrations
    ):

        return


    available = set(
        range(
            len(
                concentrations
            )
        )
    )


    for candidate in sorted(
        candidates,
        key=lambda item:
            item.start,
    ):

        if not available:
            break


        best_index = min(
            available,
            key=lambda index: (

                0
                if (
                    int(
                        concentrations[
                            index
                        ][
                            "start"
                        ]
                    )
                    - candidate.end
                )
                >= -1
                else 1,

                abs(
                    int(
                        concentrations[
                            index
                        ][
                            "start"
                        ]
                    )
                    - candidate.end
                ),
            )
        )


        selected = (
            concentrations[
                best_index
            ]
        )


        candidate.concentration = (
            str(
                selected[
                    "normalized"
                ]
            )
        )


        candidate.sources.add(
            "regex"
        )


        available.remove(
            best_index
        )


# ============================================================
# CONFIANZA FINAL
# ============================================================

def _confidence(
    candidate: Candidate,
) -> float:

    score = 0.0


    if (
        candidate.dictionary_mode
        == "exact"
    ):

        score += 0.55


    elif (
        candidate.dictionary_mode
        == "fuzzy"
    ):

        score += 0.35


    if (
        candidate.dictionary_ruler
    ):

        score += 0.20


    if (
        candidate.statistical_ner
    ):

        score += 0.20


    if (
        candidate.concentration
    ):

        score += 0.25


    return max(
        0.0,
        min(
            1.0,
            round(
                score,
                2,
            )
        )
    )


# ============================================================
# CANDIDATOS DEL DICCIONARIO
# ============================================================

def _dictionary_candidates(
    line: str,
    ocr_confidence: float,
) -> list[
    Candidate
]:

    result = (
        analyze_ocr_text(
            line,
            ocr_confidence,
        )
    )


    recognized = [

        item

        for item
        in result.get(
            "recognized_terms",
            []
        )

        if (
            item.get(
                "category"
            )
            in COMPONENT_CATEGORIES
        )
    ]


    # ========================================================
    # SI EXISTEN COINCIDENCIAS EXACTAS,
    # USARLAS ANTES QUE FUZZY.
    #
    # Esto evita:
    #
    # ACIDO SALICILICO
    # -> Ácido Acetil salicílico
    #
    # cuando ya existe:
    #
    # Ácido salicílico
    # ========================================================

    exact_items = [

        item

        for item
        in recognized

        if (
            item.get(
                "mode"
            )
            == "exact"
        )
    ]


    if exact_items:

        selected_items = (
            exact_items
        )

    else:

        selected_items = [

            item

            for item
            in recognized

            if (
                item.get(
                    "mode"
                )
                != "fuzzy"

                or float(
                    item.get(
                        "confidence"
                    )
                    or 0
                )
                >= 0.88
            )
        ]


    candidates = []


    for item in selected_items:

        match_text = str(
            item.get(
                "match"
            )
            or item.get(
                "term"
            )
            or ""
        ).strip()


        span = (
            _find_span(
                line,
                match_text,
            )
        )


        if span is None:

            span = (
                _find_span(
                    line,
                    str(
                        item.get(
                            "term"
                        )
                        or ""
                    ),
                )
            )


        if span is None:
            continue


        candidates.append(

            Candidate(

                name=str(
                    item.get(
                        "term"
                    )
                    or match_text
                ),

                start=
                    span[0],

                end=
                    span[1],

                category=str(
                    item.get(
                        "category"
                    )
                    or ""
                )
                or None,

                dictionary_confidence=
                    float(
                        item.get(
                            "confidence"
                        )
                        or 0
                    ),

                dictionary_mode=
                    str(
                        item.get(
                            "mode"
                        )
                        or ""
                    ),

                sources={
                    "dictionary"
                },
            )
        )


    return candidates


# ============================================================
# CANDIDATOS NER
#
# El NER puede proponer un ingrediente,
# pero para aceptarlo después deberá tener
# concentración REAL del regex.
# ============================================================

def _ner_candidates(
    entities: list[
        dict[str, Any]
    ],
) -> list[
    Candidate
]:

    candidates = []


    for entity in entities:

        if (
            entity.get(
                "label"
            )
            != "INSUMO"
        ):

            continue


        source = str(
            entity.get(
                "source"
            )
            or "statistical_ner"
        )


        name = str(
            entity.get(
                "canonical"
            )
            or entity.get(
                "text"
            )
            or ""
        ).strip()


        if not name:
            continue


        candidates.append(

            Candidate(

                name=
                    name,

                start=int(
                    entity[
                        "line_start"
                    ]
                ),

                end=int(
                    entity[
                        "line_end"
                    ]
                ),

                statistical_ner=(
                    source
                    == "statistical_ner"
                ),

                dictionary_ruler=(
                    source
                    == "dictionary_ruler"
                ),

                sources={
                    (
                        "ner"

                        if source
                        == "statistical_ner"

                        else "dictionary_ruler"
                    )
                },
            )
        )


    return candidates


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def fuse_ingredient_entities(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    """
    Fusión híbrida:

    OCR
        +
    Diccionario
        +
    NER
        +
    Regex

    SALIDA VISIBLE:

        INSUMO
        CONCENTRACIÓN

    Reglas:

    1. Diccionario exacto + concentración -> aceptar.

    2. Fuzzy >= 88% + concentración -> aceptar.

    3. NER + concentración NUMÉRICA del regex -> aceptar.

    4. Base exacta + c.s.p. -> aceptar sin concentración.

    5. Líneas administrativas -> rechazar.

    6. Nunca utilizar concentraciones inventadas por el NER.
    """

    text = (
        text
        or ""
    ).strip()


    # ========================================================
    # NER COMPLETO
    # ========================================================

    ner_result = (
        extract_ner_entities(
            text
        )
    )


    ner_entities = (
        ner_result.get(
            "entities",
            []
        )
    )


    line_records = []


    # ========================================================
    # PROCESAR LÍNEAS
    # ========================================================

    for (
        line_number,
        (
            line_start,
            line_end,
            line,
        )
    ) in enumerate(
        _line_spans(
            text
        ),
        start=1,
    ):

        administrative = (
            _is_administrative(
                line
            )
        )


        section_header = (
            _is_section_header(
                line
            )
        )


        line_entities = (
            _entities_for_line(
                ner_entities,
                line_start,
                line_end,
            )
        )


        # ----------------------------------------------------
        # REGEX
        # ----------------------------------------------------

        regex_result = (
            extract_regex_entities(
                line
            )
        )


        concentrations = [

            {
                "normalized":
                    item[
                        "normalized"
                    ],

                "start":
                    item[
                        "start"
                    ],

                "end":
                    item[
                        "end"
                    ],

                "source":
                    "regex",
            }

            for item
            in regex_result.get(
                "concentrations",
                []
            )
        ]


        # ----------------------------------------------------
        # SI ES ADMINISTRATIVO:
        # NO GENERAR CANDIDATOS.
        # ----------------------------------------------------

        if (
            administrative
            or section_header
        ):

            line_records.append(

                {
                    "line_number":
                        line_number,

                    "line":
                        line,

                    "administrative":
                        True,

                    "candidates":
                        [],

                    "concentrations":
                        concentrations,
                }
            )

            continue


        # ----------------------------------------------------
        # DICCIONARIO
        # ----------------------------------------------------

        dictionary_candidates = (
            _dictionary_candidates(
                line,
                ocr_confidence,
            )
        )


        # ----------------------------------------------------
        # NER
        # ----------------------------------------------------

        ner_candidates = (
            _ner_candidates(
                line_entities
            )
        )


        # ----------------------------------------------------
        # FUSIONAR
        # ----------------------------------------------------

        candidates = (
            _merge_candidates(
                [
                    *dictionary_candidates,
                    *ner_candidates,
                ]
            )
        )


        # ----------------------------------------------------
        # ASIGNAR CONCENTRACIONES
        # ----------------------------------------------------

        _pair_concentrations(
            candidates,
            concentrations,
        )


        line_records.append(

            {
                "line_number":
                    line_number,

                "line":
                    line,

                "administrative":
                    False,

                "candidates":
                    candidates,

                "concentrations":
                    concentrations,
            }
        )


    # ========================================================
    # CASO:
    #
    # Minoxidil
    # 5%
    #
    # Solo usamos concentración regex real.
    # ========================================================

    for index, record in enumerate(
        line_records[:-1]
    ):

        next_record = (
            line_records[
                index + 1
            ]
        )


        if (
            record[
                "administrative"
            ]
            or next_record[
                "administrative"
            ]
        ):

            continue


        if (
            len(
                record[
                    "candidates"
                ]
            )
            != 1
        ):

            continue


        candidate = (
            record[
                "candidates"
            ][0]
        )


        if candidate.concentration:
            continue


        if next_record[
            "candidates"
        ]:

            continue


        if (
            len(
                next_record[
                    "concentrations"
                ]
            )
            != 1
        ):

            continue


        candidate.concentration = str(
            next_record[
                "concentrations"
            ][0][
                "normalized"
            ]
        )


        candidate.sources.add(
            "regex_next_line"
        )


    # ========================================================
    # DECISIÓN FINAL
    # ========================================================

    ingredients = []

    rejected = []


    for record in line_records:

        for candidate in (
            record[
                "candidates"
            ]
        ):

            # ------------------------------------------------
            # DICCIONARIO EXACTO
            # ------------------------------------------------

            exact_dictionary = (

                candidate.dictionary_mode
                == "exact"

                or candidate.dictionary_ruler
            )


            # ------------------------------------------------
            # FUZZY FUERTE
            # ------------------------------------------------

            strong_fuzzy = (

                candidate.dictionary_mode
                == "fuzzy"

                and candidate.dictionary_confidence
                >= 0.88
            )


            dictionary_signal = (

                exact_dictionary

                or strong_fuzzy
            )


            # ------------------------------------------------
            # CONCENTRACIÓN REAL
            # ------------------------------------------------

            has_concentration = bool(
                candidate.concentration
            )


            # ------------------------------------------------
            # BASE + CSP
            # ------------------------------------------------

            base_with_csp = (

                candidate.category
                in BASE_CATEGORIES

                and exact_dictionary

                and bool(
                    CSP_PATTERN.search(
                        record[
                            "line"
                        ]
                    )
                )
            )


            # ------------------------------------------------
            # REGLAS DE ACEPTACIÓN
            # ------------------------------------------------

            accepted = (

                # Diccionario confiable + concentración
                (
                    dictionary_signal
                    and has_concentration
                )

                # NER estadístico + concentración regex real
                or (
                    candidate.statistical_ner
                    and has_concentration
                )

                # Base exacta + c.s.p.
                or base_with_csp
            )


            if base_with_csp:

                candidate.sources.add(
                    "csp_context"
                )


            confidence = (
                _confidence(
                    candidate
                )
            )


            payload = {

                "ingredient":
                    candidate.name,

                "concentration":
                    candidate.concentration,

                "confidence":
                    confidence,

                "sources":
                    sorted(
                        candidate.sources
                    ),

                "source_line":
                    record[
                        "line"
                    ],

                "line_number":
                    record[
                        "line_number"
                    ],
            }


            if accepted:

                ingredients.append(
                    payload
                )

            else:

                rejected.append(
                    payload
                )


    # ========================================================
    # DEDUPLICACIÓN
    #
    # NO fusionamos:
    #
    # Minoxidil 2.5 mg
    # Minoxidil 5%
    #
    # porque son dos registros diferentes.
    # ========================================================

    unique: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}


    for item in ingredients:

        key = (

            _simple_norm(
                str(
                    item[
                        "ingredient"
                    ]
                )
            ),

            _simple_norm(
                str(
                    item.get(
                        "concentration"
                    )
                    or ""
                )
            ),
        )


        current = (
            unique.get(
                key
            )
        )


        if (
            current is None

            or float(
                item[
                    "confidence"
                ]
            )
            > float(
                current[
                    "confidence"
                ]
            )
        ):

            unique[
                key
            ] = item


    final_ingredients = sorted(

        unique.values(),

        key=lambda item:
            int(
                item[
                    "line_number"
                ]
            )
    )


    return {

        "ingredients":
            final_ingredients,

        "ner_entities":
            ner_entities,

        "ner_status":
            ner_result.get(
                "status",
                ""
            ),

        "rejected_candidates":
            rejected,
    }