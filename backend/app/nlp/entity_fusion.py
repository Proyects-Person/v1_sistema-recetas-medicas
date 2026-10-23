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
# CATEGORÍAS
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
# TEXTO ADMINISTRATIVO
# ============================================================

ADMIN_PATTERN = re.compile(

    r"(?:"

    r"\bpaciente\b|"
    r"\bnombres?\b|"
    r"\bapellidos?\b|"
    r"\bedad\b|"
    r"\bdni\b|"
    r"\btelefono\b|"
    r"\bcelular\b|"
    r"\bdireccion\b|"
    r"\bcorreo\b|"
    r"\be\s*mail\b|"

    r"\bfecha\b|"
    r"\bdiagnostico\b|"
    r"\bdx\b|"
    r"\bfirma\b|"
    r"\bsello\b|"

    r"\bcmp\b|"
    r"\brne\b|"
    r"\bruc\b|"

    r"\bmedico\b|"
    r"\bcirujano\b|"
    r"\bdermatologo\b|"

    r"\bproxima\s+cita\b|"

    r"\bavenida\b|"
    r"\bav\.?\b|"

    r"\bwww\.|"
    r"@|"

    r"\bcentral\s*:|"
    r"\bvisitanos\b|"

    r"\bpoliclinico\b|"
    r"\bhospital\b|"
    r"\bclinica\b|"
    r"\bmunicipalidad\b"

    r")",

    flags=re.IGNORECASE,
)


SECTION_HEADER_PATTERN = re.compile(

    r"^\s*(?:"

    r"dx\.?|"

    r"diagnostico\s*:?|"

    r"indicaciones?\s*:?|"

    r"fecha\s*:?|"

    r"proxima\s+cita\s*:?|"

    r"datos?\s+del\s+paciente\s*:?|"

    r"tratamiento\s*:?|"

    r"firma\s*:?"

    r")\s*$",

    flags=re.IGNORECASE,
)


# ============================================================
# INSTRUCCIONES
# ============================================================

INSTRUCTION_PATTERN = re.compile(

    r"^\s*(?:"

    r"aplicar|"
    r"usar|"
    r"tomar|"
    r"ingerir|"
    r"colocar|"
    r"administrar|"
    r"lavar|"
    r"enjuagar|"
    r"evitar|"
    r"control|"
    r"continuar"

    r")\b",

    flags=re.IGNORECASE,
)


# ============================================================
# CSP
# ============================================================

CSP_PATTERN = re.compile(

    r"\b(?:"

    r"c\s*\.?\s*s\s*\.?\s*p\s*\.?|"

    r"csp|"

    r"c\s*/\s*p"

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
            value
            or "",
        )
    )

    return "".join(
        character

        for character
        in normalized

        if unicodedata.category(
            character
        )
        != "Mn"
    )


def _simple_norm(
    value: str,
) -> str:

    value = (
        _strip_accents(
            (
                value
                or ""
            ).casefold()
        )
    )

    value = re.sub(
        r"[^a-z0-9%]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


# ============================================================
# FILTROS DE LÍNEA
# ============================================================

def _is_administrative(
    line: str,
) -> bool:

    normalized = (
        _strip_accents(
            (
                line
                or ""
            ).casefold()
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
        _strip_accents(
            (
                line
                or ""
            ).casefold()
        )
    )

    return bool(
        SECTION_HEADER_PATTERN.fullmatch(
            normalized
        )
    )


def _is_instruction(
    line: str,
) -> bool:

    normalized = (
        _strip_accents(
            (
                line
                or ""
            ).casefold()
        )
    )

    return bool(
        INSTRUCTION_PATTERN.search(
            normalized
        )
    )


# ============================================================
# BUSCAR TODAS LAS APARICIONES
# ============================================================

def _find_all_spans(
    line: str,
    value: str,
) -> list[
    tuple[
        int,
        int,
    ]
]:

    if (
        not line
        or not value
    ):

        return []


    # --------------------------------------------------------
    # BÚSQUEDA LITERAL
    # --------------------------------------------------------

    literal = list(
        re.finditer(
            re.escape(
                value
            ),
            line,
            flags=re.IGNORECASE,
        )
    )

    if literal:

        return [

            (
                match.start(),
                match.end(),
            )

            for match
            in literal
        ]


    # --------------------------------------------------------
    # IGNORANDO TILDES
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

    spans: list[
        tuple[
            int,
            int,
        ]
    ] = []

    start = 0

    while True:

        index = (
            normalized_line.find(
                normalized_value,
                start,
            )
        )

        if index < 0:
            break

        spans.append(
            (
                index,
                index
                + len(
                    normalized_value
                ),
            )
        )

        start = (
            index
            + max(
                1,
                len(
                    normalized_value
                ),
            )
        )

    return spans


def _find_span(
    line: str,
    value: str,
) -> tuple[
    int,
    int,
] | None:

    spans = (
        _find_all_spans(
            line,
            value,
        )
    )

    return (
        spans[0]
        if spans
        else None
    )


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
        text
        or "",
    ):

        raw = (
            match.group(
                0
            )
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
            + len(
                clean
            )
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

    result: list[
        dict[str, Any]
    ] = []

    for entity in entities:

        start = int(
            entity.get(
                "start"
            )
            or 0
        )

        end = int(
            entity.get(
                "end"
            )
            or 0
        )

        if (
            start
            < line_start

            or end
            > line_end
        ):

            continue

        copied = dict(
            entity
        )

        copied[
            "start"
        ] = (
            start
            - line_start
        )

        copied[
            "end"
        ] = (
            end
            - line_start
        )

        result.append(
            copied
        )

    return result


# ============================================================
# DICCIONARIO
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
            [],
        )

        if item.get(
            "category"
        )
        in COMPONENT_CATEGORIES
    ]

    candidates: list[
        Candidate
    ] = []

    for item in recognized:

        mode = str(
            item.get(
                "mode"
            )
            or ""
        )

        confidence = float(
            item.get(
                "confidence"
            )
            or 0.0
        )

        if (
            mode
            == "fuzzy"

            and confidence
            < 0.88
        ):

            continue

        match_text = str(
            item.get(
                "match"
            )
            or item.get(
                "term"
            )
            or ""
        ).strip()

        canonical = str(
            item.get(
                "term"
            )
            or match_text
        ).strip()

        spans = (
            _find_all_spans(
                line,
                match_text,
            )
        )

        if (
            not spans
            and canonical
            != match_text
        ):

            spans = (
                _find_all_spans(
                    line,
                    canonical,
                )
            )

        for (
            start,
            end,
        ) in spans:

            candidates.append(

                Candidate(

                    name=
                        canonical,

                    start=
                        start,

                    end=
                        end,

                    category=
                        str(
                            item.get(
                                "category"
                            )
                            or ""
                        )
                        or None,

                    dictionary_confidence=
                        confidence,

                    dictionary_mode=
                        mode
                        or None,

                    sources={
                        "dictionary"
                    },
                )
            )

    return candidates


# ============================================================
# PROMOCIONAR NER CON DICCIONARIO
# ============================================================

def _promote_ner_candidate(
    candidate: Candidate,
    surface_text: str,
) -> None:

    result = (
        analyze_ocr_text(
            surface_text,
            1.0,
        )
    )

    possible = [

        item

        for item
        in result.get(
            "recognized_terms",
            [],
        )

        if item.get(
            "category"
        )
        in COMPONENT_CATEGORIES
    ]

    if not possible:
        return

    best = max(

        possible,

        key=lambda item:
            float(
                item.get(
                    "confidence"
                )
                or 0.0
            ),
    )

    confidence = float(
        best.get(
            "confidence"
        )
        or 0.0
    )

    mode = str(
        best.get(
            "mode"
        )
        or ""
    )

    if (
        mode
        == "fuzzy"

        and confidence
        < 0.90
    ):

        return

    candidate.name = str(
        best.get(
            "term"
        )
        or candidate.name
    )

    candidate.category = (
        str(
            best.get(
                "category"
            )
            or candidate.category
            or ""
        )
        or None
    )

    candidate.dictionary_confidence = max(
        candidate.dictionary_confidence,
        confidence,
    )

    candidate.dictionary_mode = (
        mode
        or candidate.dictionary_mode
    )

    candidate.sources.add(
        "dictionary"
    )


# ============================================================
# CANDIDATOS NER
# ============================================================

def _ner_candidates(
    line: str,
    entities: list[
        dict[str, Any]
    ],
) -> list[
    Candidate
]:

    candidates: list[
        Candidate
    ] = []

    for entity in entities:

        if (
            entity.get(
                "label"
            )
            != "INSUMO"
        ):

            continue

        start = int(
            entity.get(
                "start"
            )
            or 0
        )

        end = int(
            entity.get(
                "end"
            )
            or 0
        )

        if end <= start:
            continue

        source = str(
            entity.get(
                "source"
            )
            or "statistical_ner"
        )

        surface = (

            line[
                start:
                end
            ].strip()

            or str(
                entity.get(
                    "text"
                )
                or ""
            ).strip()
        )

        canonical = str(
            entity.get(
                "canonical"
            )
            or ""
        ).strip()


        # ----------------------------------------------------
        # DESCARTAR BASURA DEL NER
        #
        # Ejemplos detectados en pruebas:
        #
        # +
        # %
        # números
        #
        # Esos elementos no pueden competir con ingredientes.
        # ----------------------------------------------------

        surface_norm = (
            _simple_norm(
                surface
            )
        )

        if not re.search(
            (
                r"["
                r"A-Za-z"
                r"ÁÉÍÓÚÜÑ"
                r"áéíóúüñ"
                r"]"
            ),
            surface,
        ):

            continue

        if len(
            surface_norm.replace(
                " ",
                "",
            )
        ) < 3:

            continue


        candidate = Candidate(

            name=
                canonical
                or surface,

            start=
                start,

            end=
                end,

            statistical_ner=
                (
                    source
                    == "statistical_ner"
                ),

            dictionary_ruler=
                (
                    source
                    == "dictionary_ruler"
                ),

            dictionary_confidence=
                (
                    1.0
                    if source
                    == "dictionary_ruler"
                    else 0.0
                ),

            dictionary_mode=
                (
                    "exact"
                    if source
                    == "dictionary_ruler"
                    else None
                ),

            sources={
                (
                    "dictionary_ruler"
                    if source
                    == "dictionary_ruler"
                    else "ner"
                )
            },
        )

        if (
            source
            == "dictionary_ruler"
        ):

            candidate.category = (
                "principio_activo"
            )

        else:

            _promote_ner_candidate(
                candidate,
                surface,
            )

        candidates.append(
            candidate
        )

    return candidates


# ============================================================
# OVERLAP
# ============================================================

def _overlap(
    left: Candidate,
    right: Candidate,
) -> bool:

    return (

        left.start
        < right.end

        and left.end
        > right.start
    )


# ============================================================
# CALIDAD DEL CANDIDATO
# ============================================================

def _candidate_quality(
    candidate: Candidate,
) -> tuple[
    int,
    float,
    int,
    int,
]:

    return (

        (
            1
            if candidate.dictionary_ruler
            else 0
        ),

        float(
            candidate.dictionary_confidence
        ),

        (
            1
            if candidate.dictionary_mode
            == "exact"
            else 0
        ),

        candidate.end
        - candidate.start,
    )


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

            same_name = (

                _simple_norm(
                    candidate.name
                )

                ==

                _simple_norm(
                    existing.name
                )
            )

            same_occurrence = (

                _overlap(
                    candidate,
                    existing,
                )

                or (
                    same_name

                    and abs(
                        candidate.start
                        - existing.start
                    )
                    <= 2

                    and abs(
                        candidate.end
                        - existing.end
                    )
                    <= 2
                )
            )

            if same_occurrence:

                target = (
                    existing
                )

                break

        if target is None:

            merged.append(
                candidate
            )

            continue

        if (
            _candidate_quality(
                candidate
            )

            >

            _candidate_quality(
                target
            )
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

                or target.category
            )

            target.dictionary_confidence = max(

                target.dictionary_confidence,

                candidate.dictionary_confidence,
            )

            target.dictionary_mode = (

                candidate.dictionary_mode

                or target.dictionary_mode
            )

        elif (
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


    ordered_candidates = sorted(

        candidates,

        key=lambda item: (
            item.start,
            item.end,
        ),
    )


    ordered_concentrations = sorted(

        concentrations,

        key=lambda item: (

            int(
                item[
                    "start"
                ]
            ),

            int(
                item[
                    "end"
                ]
            ),
        ),
    )


    def assign(
        candidate: Candidate,
        concentration: dict[str, Any],
    ) -> None:

        candidate.concentration = str(
            concentration[
                "normalized"
            ]
        )

        candidate.sources.add(
            "regex"
        )


    # ========================================================
    # CASO:
    #
    # Ivermectina + Mometasona 1% + 0.1%
    #
    # Todos los insumos aparecen antes de las concentraciones.
    #
    # Debe quedar:
    #
    # Ivermectina -> 1%
    # Mometasona -> 0.1%
    # ========================================================

    if (

        len(
            ordered_candidates
        )

        ==

        len(
            ordered_concentrations
        )

        and max(
            candidate.end

            for candidate
            in ordered_candidates
        )

        <=

        min(
            int(
                concentration[
                    "start"
                ]
            )

            for concentration
            in ordered_concentrations
        )
    ):

        for (
            candidate,
            concentration,
        ) in zip(
            ordered_candidates,
            ordered_concentrations,
        ):

            assign(
                candidate,
                concentration,
            )

        return


    # ========================================================
    # CASO INVERSO
    # ========================================================

    if (

        len(
            ordered_candidates
        )

        ==

        len(
            ordered_concentrations
        )

        and max(
            int(
                concentration[
                    "end"
                ]
            )

            for concentration
            in ordered_concentrations
        )

        <=

        min(
            candidate.start

            for candidate
            in ordered_candidates
        )
    ):

        for (
            candidate,
            concentration,
        ) in zip(
            ordered_candidates,
            ordered_concentrations,
        ):

            assign(
                candidate,
                concentration,
            )

        return


    # ========================================================
    # CASO NORMAL
    #
    # Clindamicina 1% + Niacinamida 4% + Pantenol 5%
    # ========================================================

    available = set(
        range(
            len(
                ordered_concentrations
            )
        )
    )


    for (
        index,
        candidate,
    ) in enumerate(
        ordered_candidates
    ):

        next_start = (

            ordered_candidates[
                index + 1
            ].start

            if (
                index + 1
                <
                len(
                    ordered_candidates
                )
            )

            else None
        )

        local: list[int] = []

        for concentration_index in available:

            concentration = (
                ordered_concentrations[
                    concentration_index
                ]
            )

            concentration_start = int(
                concentration[
                    "start"
                ]
            )

            if (
                concentration_start
                <
                candidate.end
                - 1
            ):

                continue

            if (
                next_start is not None

                and concentration_start
                >= next_start
            ):

                continue

            local.append(
                concentration_index
            )

        if not local:
            continue

        best_index = min(

            local,

            key=lambda position:
                int(
                    ordered_concentrations[
                        position
                    ][
                        "start"
                    ]
                ),
        )

        assign(
            candidate,
            ordered_concentrations[
                best_index
            ],
        )

        available.remove(
            best_index
        )


    pending_candidates = [

        candidate

        for candidate
        in ordered_candidates

        if not candidate.concentration
    ]


    pending_concentrations = [

        ordered_concentrations[
            position
        ]

        for position
        in sorted(

            available,

            key=lambda index:
                int(
                    ordered_concentrations[
                        index
                    ][
                        "start"
                    ]
                ),
        )
    ]


    if (

        pending_candidates

        and len(
            pending_candidates
        )

        ==

        len(
            pending_concentrations
        )
    ):

        for (
            candidate,
            concentration,
        ) in zip(
            pending_candidates,
            pending_concentrations,
        ):

            assign(
                candidate,
                concentration,
            )


# ============================================================
# CONFIANZA
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

    if candidate.dictionary_ruler:

        score += 0.20

    if candidate.statistical_ner:

        score += 0.10

    if candidate.concentration:

        score += 0.25

    return round(
        min(
            1.0,
            max(
                0.0,
                score,
            )
        ),
        2,
    )


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def fuse_ingredient_entities(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    """
    Pipeline híbrido:

        OCR
         +
        Diccionario
         +
        NER
         +
        Regex

    Salida visible:

        INSUMO
        CONCENTRACIÓN

    Reglas principales:

    1. El NER puede proponer candidatos.

    2. Un candidato visible debe tener respaldo
       del diccionario farmacéutico.

    3. Debe existir una concentración real
       reconocida por regex.

    4. Un NER estadístico por sí solo NO puede
       crear ingredientes visibles.

    5. Las bases c.s.p. se conservan como contexto
       pero no contaminan la salida visible si no
       poseen concentración.

    6. Texto administrativo e indicaciones se ignoran.
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

    ner_entities = list(
        ner_result.get(
            "entities"
        )
        or []
    )


    line_records: list[
        dict[str, Any]
    ] = []


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

            or _is_section_header(
                line
            )

            or _is_instruction(
                line
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
                [],
            )
        ]


        # ----------------------------------------------------
        # LÍNEA ADMINISTRATIVA
        # ----------------------------------------------------

        if administrative:

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
        # NER DE LA LÍNEA
        # ----------------------------------------------------

        line_entities = (
            _entities_for_line(
                ner_entities,
                line_start,
                line_end,
            )
        )


        ner_candidates = (
            _ner_candidates(
                line,
                line_entities,
            )
        )


        # ----------------------------------------------------
        # FUSIÓN
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
        # INSUMO -> CONCENTRACIÓN
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
    # CASO MULTILÍNEA
    #
    # Minoxidil
    # 5%
    # ========================================================

    for (
        index,
        record,
    ) in enumerate(
        line_records[
            :-1
        ]
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

        candidate: Candidate = (
            record[
                "candidates"
            ][0]
        )

        if candidate.concentration:
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

    ingredients: list[
        dict[str, Any]
    ] = []

    rejected: list[
        dict[str, Any]
    ] = []


    for record in line_records:

        for candidate in record[
            "candidates"
        ]:

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
            # CONCENTRACIÓN
            # ------------------------------------------------

            has_concentration = bool(
                candidate.concentration
            )


            # ------------------------------------------------
            # SALIDA VISIBLE
            #
            # No basta con que NER diga que algo es un INSUMO.
            #
            # Debe existir:
            #
            # diccionario + concentración real.
            # ------------------------------------------------

            accepted = (

                dictionary_signal

                and has_concentration
            )


            reason = (
                "accepted"
            )


            if not accepted:

                if (
                    candidate.category
                    in BASE_CATEGORIES

                    and CSP_PATTERN.search(
                        record[
                            "line"
                        ]
                    )
                ):

                    reason = (
                        "base_csp_without_"
                        "explicit_concentration"
                    )

                    candidate.sources.add(
                        "csp_context"
                    )

                elif (
                    candidate.statistical_ner
                    and not dictionary_signal
                ):

                    reason = (
                        "ner_without_"
                        "dictionary_support"
                    )

                elif (
                    dictionary_signal
                    and not has_concentration
                ):

                    reason = (
                        "ingredient_without_"
                        "concentration"
                    )

                else:

                    reason = (
                        "insufficient_evidence"
                    )


            payload = {

                "ingredient":
                    candidate.name,

                "concentration":
                    candidate.concentration,

                "confidence":
                    _confidence(
                        candidate
                    ),

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

                rejected_payload = dict(
                    payload
                )

                rejected_payload[
                    "reason"
                ] = reason

                rejected.append(
                    rejected_payload
                )


    # ========================================================
    # DEDUPLICAR SOLO MISMO PAR
    #
    # Minoxidil 2.5 mg
    # Minoxidil 5%
    #
    # deben seguir siendo DOS registros.
    # ========================================================

    unique: dict[
        tuple[
            str,
            str,
        ],
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

            >

            float(
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

        key=lambda item: (

            int(
                item[
                    "line_number"
                ]
            ),

            str(
                item[
                    "ingredient"
                ]
            ),
        ),
    )


    # ========================================================
    # RESULTADO
    # ========================================================

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