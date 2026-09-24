"""
Postprocesamiento farmacéutico para OCR.

Este módulo:

1. Conserva el texto original del OCR.
2. Busca coincidencias exactas.
3. Busca alias.
4. Utiliza fuzzy matching únicamente cuando
   NO existe ya una coincidencia exacta para
   esa misma porción del texto.

Las sugerencias son apoyo para el químico
farmacéutico y no sustituyen su validación.
"""

from __future__ import annotations

import json
import re
import unicodedata

from dataclasses import dataclass

from difflib import SequenceMatcher

from pathlib import Path

from typing import Any


# ============================================================
# DICCIONARIO
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
}


# ============================================================
# CONFUSIONES OCR
# ============================================================

OCR_CONFUSIONS = {

    "0": "o",

    "1": "l",

    "5": "s",

    "8": "b",

    "@": "a",

    "€": "e",
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


def normalize_for_match(
    value: str,
) -> str:

    value = (
        _strip_accents(
            (
                value
                or ""
            ).lower()
        )
    )


    value = (
        value
        .replace(
            "º",
            ""
        )
        .replace(
            "°",
            ""
        )
    )


    value = (
        value
        .replace(
            "/",
            " "
        )
        .replace(
            "-",
            " "
        )
    )


    value = re.sub(
        r"[^a-z0-9%.,\s]",
        " ",
        value,
    )


    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


    return value


def normalize_token(
    value: str,
) -> str:

    value = (
        normalize_for_match(
            value
        )
    )


    if (
        len(value)
        >= 4
    ):

        value = "".join(

            OCR_CONFUSIONS.get(
                character,
                character,
            )

            for character
            in value
        )


    return value


# ============================================================
# TOKENIZACIÓN
# ============================================================

def split_tokens(
    value: str,
) -> list[str]:

    return re.findall(

        r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+"
        r"|"
        r"\d+(?:[.,]\d+)?%?",

        value,
    )


# ============================================================
# CARGAR DICCIONARIO
# ============================================================

def load_dictionary(
) -> list[
    DictionaryTerm
]:

    data = json.loads(

        DICTIONARY_PATH.read_text(
            encoding="utf-8"
        )
    )


    terms = []


    for item in (
        data.get(
            "terms",
            []
        )
    ):

        terms.append(

            DictionaryTerm(

                canonical=str(
                    item[
                        "canonical"
                    ]
                ),

                category=str(
                    item.get(
                        "category",
                        "termino"
                    )
                ),

                priority=int(
                    item.get(
                        "priority",
                        50
                    )
                ),

                aliases=tuple(

                    str(alias)

                    for alias
                    in item.get(
                        "aliases",
                        []
                    )
                ),
            )
        )


    terms.sort(

        key=lambda term: (

            -term.priority,

            term.canonical,
        )
    )


    return terms


# ============================================================
# SIMILITUD
# ============================================================

def similarity(
    a: str,
    b: str,
) -> float:

    return SequenceMatcher(

        None,

        normalize_for_match(
            a
        ),

        normalize_for_match(
            b
        ),

    ).ratio()


# ============================================================
# VENTANAS
# ============================================================

def _window_candidates(
    tokens: list[str],
    min_size: int = 1,
    max_size: int = 4,
) -> list[
    tuple[
        int,
        int,
        str,
    ]
]:

    candidates = []


    for start in range(
        len(tokens)
    ):

        for size in range(
            min_size,
            max_size + 1,
        ):

            end = (
                start
                + size
            )


            if (
                end
                <= len(tokens)
            ):

                text = " ".join(
                    tokens[
                        start:end
                    ]
                )


                candidates.append(
                    (
                        start,
                        end,
                        text,
                    )
                )


    return candidates


# ============================================================
# FORMATO %
# ============================================================

def _format_percentage_spacing(
    text: str,
) -> str:

    text = re.sub(

        r"(\d+(?:[.,]\d+)?)\s*%",

        r"\1%",

        text,
    )


    text = re.sub(

        r"\b(\d+)\s+([.,])\s+(\d+)\b",

        r"\1\2\3",

        text,
    )


    return text


# ============================================================
# REEMPLAZOS
# ============================================================

def _apply_high_confidence_replacements(
    raw_text: str,
    suggestions: list[
        dict[str, Any]
    ],
) -> str:

    suggested = (
        raw_text
    )


    for item in suggestions:

        original = str(
            item.get(
                "original",
                ""
            )
        ).strip()


        replacement = str(
            item.get(
                "suggestion",
                ""
            )
        ).strip()


        confidence = float(
            item.get(
                "confidence",
                0
            )
        )


        mode = str(
            item.get(
                "mode",
                ""
            )
        )


        if (
            not original
            or not replacement
        ):

            continue


        if (
            confidence
            < 0.78

            and mode
            != "context_rule"
        ):

            continue


        pattern = re.compile(

            re.escape(
                original
            ),

            flags=re.IGNORECASE,
        )


        suggested = (
            pattern.sub(
                replacement,
                suggested,
                count=1,
            )
        )


    return (
        _format_percentage_spacing(
            suggested
        )
        .strip()
    )


# ============================================================
# REGLAS CONTEXTUALES
# ============================================================

def _context_rules(
    raw_text: str,
) -> list[
    dict[str, Any]
]:

    normalized = (
        normalize_for_match(
            raw_text
        )
    )


    suggestions = []


    # --------------------------------------------------------
    # ALCOHOL BORICADO
    # --------------------------------------------------------

    if (
        "alcohol"
        in normalized
    ):

        tokens = (
            normalized.split()
        )


        for token in tokens:

            score = max(

                similarity(
                    token,
                    target,
                )

                for target in [

                    "boricado",

                    "boricad",

                    "borico",

                    "sonicado",
                ]
            )


            if (
                token
                not in {
                    "alcohol",
                    "alc",
                }

                and score
                >= 0.66
            ):

                percent = (
                    re.search(
                        r"\d+(?:[.,]\d+)?\s*%",
                        raw_text,
                    )
                )


                replacement = (
                    "Alcohol boricado"
                )


                if percent:

                    replacement = (
                        f"{replacement} "
                        f"{percent.group(0).replace(' ', '')}"
                    )


                suggestions.append(

                    {
                        "original":
                            raw_text.strip(),

                        "suggestion":
                            replacement,

                        "category":
                            "principio_activo_preparado",

                        "confidence":
                            round(
                                max(
                                    score,
                                    0.88,
                                ),
                                2,
                            ),

                        "reason":
                            (
                                "Patrón contextual asociado "
                                "a alcohol boricado."
                            ),

                        "mode":
                            "context_rule",
                    }
                )


                break


    return suggestions


# ============================================================
# ANALIZAR OCR
# ============================================================

def analyze_ocr_text(
    raw_text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:

    terms = (
        load_dictionary()
    )


    raw_text = (
        raw_text
        or ""
    ).strip()


    normalized_raw = (
        normalize_for_match(
            raw_text
        )
    )


    tokens_original = (
        split_tokens(
            raw_text
        )
    )


    suggestions = []

    recognized = []


    # ========================================================
    # 1. EXACTOS / ALIAS
    # ========================================================

    for term in terms:

        for form in (
            term.all_forms
        ):

            form_norm = (
                normalize_for_match(
                    form
                )
            )


            if (
                not form_norm
                or len(
                    form_norm
                )
                < 2
            ):

                continue


            pattern = (

                rf"(?<![a-z0-9])"

                rf"{re.escape(form_norm)}"

                rf"(?![a-z0-9])"
            )


            if not re.search(
                pattern,
                normalized_raw,
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


            # ------------------------------------------------
            # SI ERA ALIAS:
            # PROPONER CANÓNICO.
            # ------------------------------------------------

            if (
                form_norm
                != normalize_for_match(
                    term.canonical
                )

                and form
                not in {
                    "%",
                    "g",
                    "ml",
                    "mL",
                }
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


    # ========================================================
    # FRASES QUE YA TIENEN COINCIDENCIA EXACTA
    #
    # Esta parte corrige tu problema actual.
    # ========================================================

    exact_matches = {

        normalize_for_match(
            str(
                item.get(
                    "match",
                    ""
                )
            )
        )

        for item in recognized

        if (
            item.get(
                "mode"
            )
            == "exact"
        )
    }


    # ========================================================
    # 2. REGLAS CONTEXTUALES
    # ========================================================

    suggestions.extend(

        _context_rules(
            raw_text
        )
    )


    # ========================================================
    # 3. FUZZY
    # ========================================================

    windows = (
        _window_candidates(
            tokens_original,
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


        canonical_tokens = (
            canonical_norm.split()
        )


        if (
            not canonical_norm
            or len(
                canonical_norm
            )
            < 4
        ):

            continue


        best_score = 0.0

        best_candidate = ""


        for (
            _,
            _,
            candidate,
        ) in windows:

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


            # ------------------------------------------------
            # SI ESA FRASE YA FUE IDENTIFICADA EXACTAMENTE,
            # NO BUSCAR OTRA INTERPRETACIÓN FUZZY.
            #
            # Ejemplo:
            #
            # ACIDO SALICILICO
            #
            # ya es:
            # Ácido salicílico
            #
            # por lo tanto NO debe sugerir:
            # Ácido Acetil salicílico
            # ------------------------------------------------

            if (
                candidate_norm
                in exact_matches
            ):

                continue


            if (
                len(
                    candidate_norm
                )
                <= 3

                and len(
                    canonical_norm
                )
                > 5
            ):

                continue


            if (
                abs(
                    len(
                        candidate_norm.split()
                    )
                    - len(
                        canonical_tokens
                    )
                )
                > 1
            ):

                continue


            score = (
                similarity(
                    candidate_norm,
                    canonical_norm,
                )
            )


            if (
                score
                > best_score
            ):

                best_score = (
                    score
                )

                best_candidate = (
                    candidate
                )


        threshold = (

            0.83

            if (
                len(
                    canonical_tokens
                )
                == 1
            )

            else 0.76
        )


        if (
            term.category
            in {
                "unidad",
                "frecuencia",
                "indicacion",
            }
        ):

            threshold = (
                0.90
            )


        if (
            best_score
            < threshold
        ):

            continue


        if (
            not best_candidate
        ):

            continue


        candidate_norm = (
            normalize_for_match(
                best_candidate
            )
        )


        # ----------------------------------------------------
        # SEGUNDA PROTECCIÓN CONTRA EXACTOS
        # ----------------------------------------------------

        if (
            candidate_norm
            in exact_matches
        ):

            continue


        if (
            candidate_norm
            == canonical_norm
        ):

            continue


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


    # ========================================================
    # 4. SUGERENCIAS ÚNICAS
    # ========================================================

    suggestions_unique = {}


    for suggestion in (
        suggestions
    ):

        key = (

            normalize_for_match(
                str(
                    suggestion.get(
                        "original",
                        ""
                    )
                )
            ),

            normalize_for_match(
                str(
                    suggestion.get(
                        "suggestion",
                        ""
                    )
                )
            ),
        )


        if (
            not key[0]
            or not key[1]
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
                suggestion.get(
                    "confidence",
                    0,
                )
            )
            > float(
                current.get(
                    "confidence",
                    0,
                )
            )
        ):

            suggestions_unique[
                key
            ] = suggestion


    suggestions_out = sorted(

        suggestions_unique.values(),

        key=lambda item:

            float(
                item.get(
                    "confidence",
                    0,
                )
            ),

        reverse=True,
    )[:12]


    # ========================================================
    # 5. RECONOCIDOS ÚNICOS
    # ========================================================

    recognized_unique = {}


    for item in (
        recognized
    ):

        term = str(
            item.get(
                "term",
                ""
            )
        )


        if not term:
            continue


        current = (
            recognized_unique.get(
                term
            )
        )


        if (
            current is None

            or float(
                item.get(
                    "confidence",
                    0,
                )
            )
            > float(
                current.get(
                    "confidence",
                    0,
                )
            )
        ):

            recognized_unique[
                term
            ] = item


    recognized_out = sorted(

        recognized_unique.values(),

        key=lambda item: (

            item.get(
                "category",
                ""
            ),

            item.get(
                "term",
                ""
            ),
        ),
    )


    # ========================================================
    # 6. TEXTO NORMALIZADO
    # ========================================================

    suggested_text = (

        _apply_high_confidence_replacements(
            raw_text,
            suggestions_out,
        )

        if suggestions_out

        else ""
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
    # RESULTADO
    # ========================================================

    dictionary_data = json.loads(

        DICTIONARY_PATH.read_text(
            encoding="utf-8"
        )
    )


    return {

        "normalized_text":
            normalized_text,

        "dictionary_suggestions":
            suggestions_out,

        "recognized_terms":
            recognized_out,

        "dictionary_version":
            dictionary_data.get(
                "version"
            ),

        "warning":
            (
                "Las sugerencias son apoyo de validación "
                "y no reemplazan el criterio del "
                "químico farmacéutico."
            ),
    }