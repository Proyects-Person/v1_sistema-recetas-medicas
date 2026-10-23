"""
Postprocesamiento farmacéutico para el OCR.

Responsabilidades:

- Cargar el diccionario farmacéutico.
- Reconocer nombres canónicos y aliases.
- Reconocer términos pegados a la concentración.
- Realizar fuzzy matching conservador.
- Normalizar errores OCR.
- No inventar concentraciones.
"""

from __future__ import annotations

import json
import re
import unicodedata

from dataclasses import dataclass

from difflib import SequenceMatcher

from functools import lru_cache

from pathlib import Path

from typing import Any


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

DICTIONARY_PATH = (

    BASE_DIR
    / "dictionaries"
    / "pharmaceutical_terms.json"
)


# ============================================================
# STOPWORDS
# ============================================================

STOPWORDS = {

    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "y",
    "o",
    "a",
    "al",
    "en",
    "con",
    "para",
    "por",
    "un",
    "una",
    "uso",
    "dia",
    "día",
    "cada",
    "veces",
    "aplicar",
    "receta",
    "paciente",
    "diagnostico",
    "diagnóstico",
    "fecha",
    "firma",
    "medico",
    "médico",
}


COMPONENT_CATEGORIES = {

    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}


NON_COMPONENT_HIGH_THRESHOLD = {

    "unidad",
    "frecuencia",
    "indicacion",
    "via",
    "via_administracion",
}


# ============================================================
# MODELO
# ============================================================

@dataclass(
    frozen=True
)
class DictionaryTerm:

    canonical: str

    category: str

    priority: int

    aliases: tuple[
        str,
        ...
    ]

    @property
    def all_forms(
        self,
    ) -> tuple[
        str,
        ...
    ]:

        return (
            self.canonical,
            *self.aliases,
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


def normalize_for_match(
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

    value = (
        value.replace(
            "µ",
            "u",
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


def normalize_token(
    value: str,
) -> str:

    return (
        normalize_for_match(
            value
        )
    )


# ============================================================
# TOKENS
# ============================================================

def split_tokens(
    value: str,
) -> list[str]:

    prepared = re.sub(
        (
            r"(?<="
            r"[A-Za-zÁÉÍÓÚáéíóúÑñ]"
            r")"
            r"(?=\d)"
        ),
        " ",
        value
        or "",
    )

    prepared = re.sub(
        (
            r"(?<=\d)"
            r"(?="
            r"[A-Za-zÁÉÍÓÚáéíóúÑñ]"
            r")"
        ),
        " ",
        prepared,
    )

    return re.findall(
        (
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+"
            r"|\d+(?:[.,]\d+)?"
            r"|%"
            r"|°"
        ),
        prepared,
    )


# ============================================================
# CARGAR DICCIONARIO
# ============================================================

@lru_cache(
    maxsize=1
)
def load_dictionary(
) -> tuple[
    DictionaryTerm,
    ...
]:

    if not DICTIONARY_PATH.exists():

        return tuple()

    data = json.loads(
        DICTIONARY_PATH.read_text(
            encoding="utf-8"
        )
    )

    terms: list[
        DictionaryTerm
    ] = []

    for item in data.get(
        "terms",
        [],
    ):

        canonical = str(
            item.get(
                "canonical"
            )
            or ""
        ).strip()

        category = str(
            item.get(
                "category"
            )
            or ""
        ).strip()

        if (
            not canonical
            or not category
        ):

            continue

        aliases = tuple(

            str(
                alias
            ).strip()

            for alias
            in item.get(
                "aliases",
                [],
            )

            if str(
                alias
            ).strip()
        )

        terms.append(

            DictionaryTerm(

                canonical=
                    canonical,

                category=
                    category,

                priority=
                    int(
                        item.get(
                            "priority"
                        )
                        or 0
                    ),

                aliases=
                    aliases,
            )
        )

    return tuple(
        terms
    )


def reload_dictionary(
) -> None:

    load_dictionary.cache_clear()


# ============================================================
# SIMILITUD
# ============================================================

def similarity(
    left: str,
    right: str,
) -> float:

    left_norm = (
        normalize_for_match(
            left
        )
    )

    right_norm = (
        normalize_for_match(
            right
        )
    )

    if (
        not left_norm
        or not right_norm
    ):

        return 0.0

    return SequenceMatcher(
        None,
        left_norm,
        right_norm,
    ).ratio()


# ============================================================
# PALABRAS DEL OCR
# ============================================================

def _text_words(
    raw_text: str,
) -> list[str]:

    prepared = re.sub(
        (
            r"\d+(?:[.,]\d+)?"
            r"\s*"
            r"(?:"
            r"%|mg|mcg|ug|µg|"
            r"g|kg|ml|mL|cc|°"
            r")?"
        ),
        " ",
        raw_text
        or "",
        flags=re.IGNORECASE,
    )

    return re.findall(
        (
            r"["
            r"A-Za-z"
            r"ÁÉÍÓÚÜÑ"
            r"áéíóúüñ"
            r"]+"
        ),
        prepared,
    )


# ============================================================
# VENTANAS PARA FUZZY
# ============================================================

def _window_candidates(
    raw_text: str,
    min_size: int = 1,
    max_size: int = 4,
) -> list[str]:

    words = (
        _text_words(
            raw_text
        )
    )

    result: list[str] = []

    for size in range(
        min_size,
        max_size + 1,
    ):

        for start in range(
            0,
            len(words)
            - size
            + 1,
        ):

            candidate = " ".join(
                words[
                    start:
                    start
                    + size
                ]
            ).strip()

            if candidate:

                result.append(
                    candidate
                )

    return result


# ============================================================
# EXACT MATCH
#
# MUY IMPORTANTE:
#
# Permite:
#
# Minoxidil5%
# Urea20%
# Clobetasol0.05%
#
# Antes esos casos podían perderse porque el número estaba
# pegado al nombre.
# ============================================================

def _exact_form_present(
    normalized_raw: str,
    normalized_form: str,
) -> bool:

    if not normalized_form:

        return False

    pattern = (

        rf"(?<![a-z0-9])"

        rf"{re.escape(normalized_form)}"

        rf"(?![a-z])"
    )

    return bool(
        re.search(
            pattern,
            normalized_raw,
        )
    )


# ============================================================
# UMBRAL FUZZY
# ============================================================

def _fuzzy_threshold(
    term: DictionaryTerm,
) -> float:

    canonical_norm = (
        normalize_for_match(
            term.canonical
        )
    )

    token_count = len(
        canonical_norm.split()
    )

    canonical_length = len(
        canonical_norm.replace(
            " ",
            "",
        )
    )

    if (
        term.category
        in NON_COMPONENT_HIGH_THRESHOLD
    ):

        return 0.93

    if token_count >= 2:

        return 0.86

    if canonical_length <= 5:

        return 0.90

    return 0.86


# ============================================================
# REEMPLAZAR FRASE
# ============================================================

def _replace_phrase(
    text: str,
    original: str,
    replacement: str,
) -> str:

    if (
        not original
        or not replacement
    ):

        return text

    return re.sub(
        re.escape(
            original
        ),
        replacement,
        text,
        flags=re.IGNORECASE,
    )


# ============================================================
# APLICAR NORMALIZACIONES
# ============================================================

def _apply_high_confidence_replacements(
    raw_text: str,
    suggestions: list[
        dict[str, Any]
    ],
) -> str:

    result = raw_text

    ordered = sorted(
        suggestions,

        key=lambda item:
            len(
                str(
                    item.get(
                        "original"
                    )
                    or ""
                )
            ),

        reverse=True,
    )

    for item in ordered:

        confidence = float(
            item.get(
                "confidence"
            )
            or 0.0
        )

        if confidence < 0.90:
            continue

        original = str(
            item.get(
                "original"
            )
            or ""
        ).strip()

        suggestion = str(
            item.get(
                "suggestion"
            )
            or ""
        ).strip()

        if (
            not original
            or not suggestion
        ):

            continue

        result = (
            _replace_phrase(
                result,
                original,
                suggestion,
            )
        )

    return result


# ============================================================
# ANALIZAR OCR
# ============================================================

def analyze_ocr_text(
    raw_text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    raw_text = (
        raw_text
        or ""
    ).strip()

    normalized_raw = (
        normalize_for_match(
            raw_text
        )
    )

    terms = (
        load_dictionary()
    )

    recognized: list[
        dict[str, Any]
    ] = []

    suggestions: list[
        dict[str, Any]
    ] = []

    exact_covered_forms: set[
        str
    ] = set()


    # ========================================================
    # 1. EXACTOS Y ALIASES
    # ========================================================

    for term in terms:

        forms = sorted(
            set(
                term.all_forms
            ),

            key=lambda value:
                len(
                    normalize_for_match(
                        value
                    )
                ),

            reverse=True,
        )

        for form in forms:

            form_norm = (
                normalize_for_match(
                    form
                )
            )

            if len(
                form_norm
            ) < 2:

                continue

            if not _exact_form_present(
                normalized_raw,
                form_norm,
            ):

                continue

            recognized.append(

                {
                    "term":
                        term.canonical,

                    "category":
                        term.category,

                    "match":
                        form,

                    "confidence":
                        1.0,

                    "mode":
                        "exact",
                }
            )

            exact_covered_forms.add(
                form_norm
            )

            if (
                form_norm
                != normalize_for_match(
                    term.canonical
                )
            ):

                suggestions.append(

                    {
                        "original":
                            form,

                        "suggestion":
                            term.canonical,

                        "category":
                            term.category,

                        "confidence":
                            1.0,

                        "reason":
                            (
                                "Alias reconocido en "
                                "el diccionario farmacéutico."
                            ),

                        "mode":
                            "alias",
                    }
                )

            break


    exact_canonicals = {

        normalize_for_match(
            str(
                item.get(
                    "term"
                )
                or ""
            )
        )

        for item
        in recognized

        if item.get(
            "mode"
        )
        == "exact"
    }


    # ========================================================
    # 2. FUZZY MATCHING CONSERVADOR
    # ========================================================

    windows = (
        _window_candidates(
            raw_text,
            1,
            4,
        )
    )

    for term in terms:

        canonical_norm = (
            normalize_for_match(
                term.canonical
            )
        )

        if (
            not canonical_norm
            or canonical_norm
            in exact_canonicals
        ):

            continue

        threshold = (
            _fuzzy_threshold(
                term
            )
        )

        best_candidate = ""

        best_score = 0.0

        target_forms = [

            term.canonical,

            *term.aliases,
        ]

        for candidate in windows:

            candidate_norm = (
                normalize_for_match(
                    candidate
                )
            )

            if (
                not candidate_norm
                or candidate_norm
                in STOPWORDS
            ):

                continue

            if (
                candidate_norm
                in exact_covered_forms
            ):

                continue

            candidate_tokens = (
                candidate_norm.split()
            )

            for target_form in target_forms:

                target_norm = (
                    normalize_for_match(
                        target_form
                    )
                )

                if not target_norm:
                    continue

                target_tokens = (
                    target_norm.split()
                )

                if abs(
                    len(
                        candidate_tokens
                    )
                    - len(
                        target_tokens
                    )
                ) > 1:

                    continue

                score = (
                    SequenceMatcher(
                        None,
                        candidate_norm,
                        target_norm,
                    ).ratio()
                )

                if score > best_score:

                    best_score = (
                        score
                    )

                    best_candidate = (
                        candidate
                    )

        if (
            not best_candidate
            or best_score
            < threshold
        ):

            continue

        recognized.append(

            {
                "term":
                    term.canonical,

                "category":
                    term.category,

                "match":
                    best_candidate,

                "confidence":
                    round(
                        best_score,
                        2,
                    ),

                "mode":
                    "fuzzy",
            }
        )

        suggestions.append(

            {
                "original":
                    best_candidate,

                "suggestion":
                    term.canonical,

                "category":
                    term.category,

                "confidence":
                    round(
                        best_score,
                        2,
                    ),

                "reason":
                    (
                        "Coincidencia aproximada "
                        "con el diccionario farmacéutico."
                    ),

                "mode":
                    "fuzzy",
            }
        )


    # ========================================================
    # 3. RECONOCIDOS ÚNICOS
    # ========================================================

    recognized_unique: dict[
        tuple[
            str,
            str,
        ],
        dict[str, Any],
    ] = {}

    for item in recognized:

        key = (

            normalize_for_match(
                str(
                    item.get(
                        "term"
                    )
                    or ""
                )
            ),

            normalize_for_match(
                str(
                    item.get(
                        "match"
                    )
                    or ""
                )
            ),
        )

        current = (
            recognized_unique.get(
                key
            )
        )

        if (
            current is None

            or float(
                item.get(
                    "confidence"
                )
                or 0
            )
            > float(
                current.get(
                    "confidence"
                )
                or 0
            )
        ):

            recognized_unique[
                key
            ] = item


    recognized_out = sorted(

        recognized_unique.values(),

        key=lambda item: (

            -float(
                item.get(
                    "confidence"
                )
                or 0
            ),

            -len(
                str(
                    item.get(
                        "match"
                    )
                    or ""
                )
            ),

            str(
                item.get(
                    "term"
                )
                or ""
            ),
        ),
    )


    # ========================================================
    # 4. SUGERENCIAS ÚNICAS
    # ========================================================

    suggestions_unique: dict[
        tuple[
            str,
            str,
        ],
        dict[str, Any],
    ] = {}

    for item in suggestions:

        key = (

            normalize_for_match(
                str(
                    item.get(
                        "original"
                    )
                    or ""
                )
            ),

            normalize_for_match(
                str(
                    item.get(
                        "suggestion"
                    )
                    or ""
                )
            ),
        )

        if not all(
            key
        ):

            continue

        current = (
            suggestions_unique.get(
                key
            )
        )

        if (
            current is None

            or float(
                item.get(
                    "confidence"
                )
                or 0
            )
            > float(
                current.get(
                    "confidence"
                )
                or 0
            )
        ):

            suggestions_unique[
                key
            ] = item


    suggestions_out = sorted(

        suggestions_unique.values(),

        key=lambda item:
            float(
                item.get(
                    "confidence"
                )
                or 0
            ),

        reverse=True,
    )[:20]


    # ========================================================
    # 5. TEXTO NORMALIZADO
    # ========================================================

    suggested_text = (
        _apply_high_confidence_replacements(
            raw_text,
            suggestions_out,
        )
    )

    normalized_text = (

        suggested_text

        if (
            suggested_text
            and suggested_text.strip()
            != raw_text.strip()
        )

        else None
    )


    # ========================================================
    # VERSIÓN
    # ========================================================

    try:

        dictionary_data = (
            json.loads(
                DICTIONARY_PATH.read_text(
                    encoding="utf-8"
                )
            )
        )

        version = (
            dictionary_data.get(
                "version"
            )
        )

    except Exception:

        version = None


    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        "normalized_text":
            normalized_text,

        "dictionary_suggestions":
            suggestions_out,

        "recognized_terms":
            recognized_out,

        "dictionary_version":
            version,

        "warning":
            (
                "Las sugerencias son apoyo de validación "
                "y no reemplazan el criterio del "
                "químico farmacéutico."
            ),
    }