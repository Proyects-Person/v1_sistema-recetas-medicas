from __future__ import annotations

import json
import re
import unicodedata

from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

DICTIONARY_DIR = (
    BASE_DIR
    / "dictionaries"
)

TARGET = (
    DICTIONARY_DIR
    / "pharmaceutical_terms.json"
)

BACKUP_SOURCE = (
    DICTIONARY_DIR
    / "pharmaceutical_terms.backup.json"
)

ENRICHED_SOURCE = (
    DICTIONARY_DIR
    / "pharmaceutical_ingredients_enriched.json"
)

SAFETY_BACKUP = (
    DICTIONARY_DIR
    / "pharmaceutical_terms.before_metric_fix.json"
)


COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}


# ============================================================
# TÉRMINOS QUE FALTABAN EN EL DICCIONARIO ACTIVO
# ============================================================

MANUAL_TERMS: list[
    dict[str, Any]
] = [

    {
        "canonical":
            "Cetirizina",

        "category":
            "principio_activo",

        "priority":
            105,

        "aliases": [
            "Cetirizine",
            "Cetiricina",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "10 mg",
        ],
    },

    {
        "canonical":
            "Sulfato ferroso",

        "category":
            "principio_activo",

        "priority":
            105,

        "aliases": [
            "Sulfato feroso",
            "Ferrous sulfate",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "300 mg",
        ],
    },

    {
        "canonical":
            "Pramoxina",

        "category":
            "principio_activo",

        "priority":
            100,

        "aliases": [
            "Pramoxine",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "5%",
        ],
    },

    {
        "canonical":
            "Sulfuro de selenio",

        "category":
            "principio_activo",

        "priority":
            100,

        "aliases": [
            "Sulfuro selenio",
            "Selenio sulfuro",
            "Sulfito de selenio",
            "Sulfito de selemio",
            "Selenium sulfide",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "2.5%",
        ],
    },
]


# ============================================================
# ALIASES Y ERRORES OCR IMPORTANTES
# ============================================================

EXTRA_ALIASES: dict[
    str,
    list[str],
] = {

    "Peróxido de benzoilo": [
        "PB",
        "PBO",
        "Perox benzoilo",
        "Peroxido de benzoilo",
        "Benzoyl peroxide",
    ],

    "Niacinamida": [
        "Nicotinamida",
        "Niacinamide",
        "Niacina",
        "Niac",
        "Nia",
    ],

    "Urea": [
        "Unea",
        "Úrea",
        "Urea pura",
        "Urea q.p.",
        "Urea qp",
    ],

    "Minoxidil": [
        "Minox",
        "Minoxdil",
        "Minoxidii",
        "Minoxidilo",
    ],

    "Clobetasol": [
        "Clobetazol",
        "Clobetasoi",
        "Clob",
        "Clobet",
        "Clobetasol propionato",
    ],

    "Triamcinolona": [
        "Triancinolona",
        "Triam",
        "Triamcinolona acetónido",
        "Triamcinolona acetonido",
    ],

    "Hidrocortisona": [
        "Hidrocortizona",
        "Hidrocortsona",
        "Hidrocort",
    ],

    "Mometasona": [
        "Mometazona",
        "Mometasone",
        "Mome",
    ],

    "Tacrolimus": [
        "Tacrolimo",
        "Tacro",
        "Tacrolimus ungüento",
        "Tacrolimus unguento",
    ],

    "Adapaleno": [
        "Adapalene",
        "Adapaleno gel",
        "Adap",
    ],

    "Clindamicina": [
        "Clindamicin",
        "Clindamcina",
        "Clindamicina HCL",
        "Clindamicina clorhidrato",
    ],

    "Ácido salicílico": [
        "Acido salicilico",
        "Ac salicilico",
        "Ac. salicilico",
        "Salic",
    ],

    "Ácido láctico": [
        "Acido lactico",
        "Lactico",
        "Lactic acid",
    ],

    "Ácido azelaico": [
        "Acido azelaico",
        "Azelaico",
        "Azelac",
    ],

    "Pantenol": [
        "Panthenol",
        "D-pantenol",
        "D pantenol",
        "Panteno",
        "Panterol",
        "Dexpantenol",
    ],

    "Piritionato de zinc": [
        "Piritionato zinc",
        "Piritionato de cinc",
        "Zinc pyrithione",
        "Zinc piritiona",
    ],

    "Isoconazol": [
        "Isoconazoi",
        "Isoconazole",
        "Isocona",
    ],
}


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _strip_accents(
    value: str,
) -> str:

    normalized = (
        unicodedata.normalize(
            "NFD",
            value or "",
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


def _key(
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
# CARGAR JSON
# ============================================================

def _load(
    path: Path,
) -> dict[str, Any]:

    if not path.exists():

        return {
            "terms": [],
        }

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# LISTA ÚNICA
# ============================================================

def _unique_strings(
    values: list[Any],
) -> list[str]:

    result: list[str] = []

    seen: set[str] = set()

    for raw in values:

        value = str(
            raw
            or ""
        ).strip()

        if not value:
            continue

        normalized = (
            _key(
                value
            )
        )

        if (
            not normalized
            or normalized
            in seen
        ):

            continue

        seen.add(
            normalized
        )

        result.append(
            value
        )

    return result


# ============================================================
# FUSIONAR UN TÉRMINO
# ============================================================

def _merge_term(
    current: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:

    merged = dict(
        current
    )

    merged[
        "canonical"
    ] = str(
        current.get(
            "canonical"
        )
        or incoming.get(
            "canonical"
        )
        or ""
    ).strip()

    merged[
        "category"
    ] = str(
        current.get(
            "category"
        )
        or incoming.get(
            "category"
        )
        or ""
    ).strip()

    merged[
        "priority"
    ] = max(
        int(
            current.get(
                "priority"
            )
            or 0
        ),
        int(
            incoming.get(
                "priority"
            )
            or 0
        ),
    )

    merged[
        "aliases"
    ] = _unique_strings(
        [
            *list(
                current.get(
                    "aliases"
                )
                or []
            ),
            *list(
                incoming.get(
                    "aliases"
                )
                or []
            ),
        ]
    )

    merged[
        "observed_strengths"
    ] = _unique_strings(
        [
            *list(
                current.get(
                    "observed_strengths"
                )
                or []
            ),
            *list(
                incoming.get(
                    "observed_strengths"
                )
                or []
            ),
        ]
    )

    merged[
        "observed_in_ner"
    ] = bool(
        current.get(
            "observed_in_ner",
            False,
        )
        or incoming.get(
            "observed_in_ner",
            False,
        )
    )

    merged[
        "observed_count"
    ] = max(
        int(
            current.get(
                "observed_count"
            )
            or 0
        ),
        int(
            incoming.get(
                "observed_count"
            )
            or 0
        ),
    )

    if not merged.get(
        "verification"
    ):

        merged[
            "verification"
        ] = incoming.get(
            "verification",
            "PENDIENTE_VALIDACION_QF",
        )

    return merged


# ============================================================
# BUSCAR DUEÑO EXISTENTE
# ============================================================

def _find_existing_owner(
    incoming: dict[str, Any],
    merged: dict[
        str,
        dict[str, Any],
    ],
) -> str | None:

    forms = [

        str(
            incoming.get(
                "canonical"
            )
            or ""
        ),

        *[
            str(
                value
                or ""
            )

            for value
            in incoming.get(
                "aliases"
            )
            or []
        ],
    ]

    form_keys = {

        _key(
            value
        )

        for value
        in forms

        if _key(
            value
        )
    }

    canonical_key = (
        _key(
            str(
                incoming.get(
                    "canonical"
                )
                or ""
            )
        )
    )

    if canonical_key in merged:

        return canonical_key

    for form_key in form_keys:

        if form_key in merged:

            return form_key

    for (
        owner_key,
        item,
    ) in merged.items():

        existing_forms = {

            _key(
                str(
                    item.get(
                        "canonical"
                    )
                    or ""
                )
            ),

            *{
                _key(
                    str(
                        alias
                        or ""
                    )
                )

                for alias
                in item.get(
                    "aliases"
                )
                or []
            },
        }

        if (
            canonical_key
            and canonical_key
            in existing_forms
        ):

            return owner_key

    return None


# ============================================================
# FUSIONAR FUENTE
# ============================================================

def _merge_source(
    source_terms: list[
        dict[str, Any]
    ],
    merged: dict[
        str,
        dict[str, Any],
    ],
    *,
    add_missing_only_components: bool,
) -> None:

    for incoming in source_terms:

        canonical = str(
            incoming.get(
                "canonical"
            )
            or ""
        ).strip()

        if not canonical:
            continue

        category = str(
            incoming.get(
                "category"
            )
            or ""
        ).strip()

        owner = (
            _find_existing_owner(
                incoming,
                merged,
            )
        )

        if owner is not None:

            merged[
                owner
            ] = _merge_term(
                merged[
                    owner
                ],
                incoming,
            )

            continue

        if (
            add_missing_only_components
            and category
            not in COMPONENT_CATEGORIES
        ):

            continue

        merged[
            _key(
                canonical
            )
        ] = dict(
            incoming
        )


# ============================================================
# ALIASES EXTRA
# ============================================================

def _apply_extra_aliases(
    merged: dict[
        str,
        dict[str, Any],
    ],
) -> None:

    for (
        canonical,
        aliases,
    ) in EXTRA_ALIASES.items():

        key = (
            _key(
                canonical
            )
        )

        item = (
            merged.get(
                key
            )
        )

        if item is None:
            continue

        item[
            "aliases"
        ] = _unique_strings(
            [
                *list(
                    item.get(
                        "aliases"
                    )
                    or []
                ),
                *aliases,
            ]
        )


# ============================================================
# EVITAR ALIASES DUPLICADOS
# ============================================================

def _clean_alias_collisions(
    terms: list[
        dict[str, Any]
    ],
) -> None:

    canonical_owner: dict[
        str,
        str,
    ] = {}

    for item in terms:

        canonical = str(
            item.get(
                "canonical"
            )
            or ""
        ).strip()

        if canonical:

            canonical_owner[
                _key(
                    canonical
                )
            ] = canonical

    ordered = sorted(
        terms,
        key=lambda item:
            int(
                item.get(
                    "priority"
                )
                or 0
            ),
        reverse=True,
    )

    alias_owner: dict[
        str,
        str,
    ] = {}

    for item in ordered:

        canonical = str(
            item.get(
                "canonical"
            )
            or ""
        ).strip()

        canonical_key = (
            _key(
                canonical
            )
        )

        cleaned: list[str] = []

        for alias in _unique_strings(
            list(
                item.get(
                    "aliases"
                )
                or []
            )
        ):

            alias_key = (
                _key(
                    alias
                )
            )

            if (
                not alias_key
                or alias_key
                == canonical_key
            ):

                continue

            other_canonical = (
                canonical_owner.get(
                    alias_key
                )
            )

            if (
                other_canonical
                and _key(
                    other_canonical
                )
                != canonical_key
            ):

                continue

            owner = (
                alias_owner.get(
                    alias_key
                )
            )

            if (
                owner
                and owner
                != canonical_key
            ):

                continue

            alias_owner[
                alias_key
            ] = canonical_key

            cleaned.append(
                alias
            )

        item[
            "aliases"
        ] = cleaned


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    if not TARGET.exists():

        raise FileNotFoundError(
            "No existe el diccionario activo: "
            f"{TARGET}"
        )

    current_data = (
        _load(
            TARGET
        )
    )

    backup_data = (
        _load(
            BACKUP_SOURCE
        )
    )

    enriched_data = (
        _load(
            ENRICHED_SOURCE
        )
    )

    if not SAFETY_BACKUP.exists():

        SAFETY_BACKUP.write_text(
            json.dumps(
                current_data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    merged: dict[
        str,
        dict[str, Any],
    ] = {}

    _merge_source(
        list(
            current_data.get(
                "terms"
            )
            or []
        ),
        merged,
        add_missing_only_components=False,
    )

    _merge_source(
        list(
            backup_data.get(
                "terms"
            )
            or []
        ),
        merged,
        add_missing_only_components=True,
    )

    _merge_source(
        list(
            enriched_data.get(
                "terms"
            )
            or []
        ),
        merged,
        add_missing_only_components=True,
    )

    _merge_source(
        MANUAL_TERMS,
        merged,
        add_missing_only_components=True,
    )

    _apply_extra_aliases(
        merged
    )

    terms = list(
        merged.values()
    )

    _clean_alias_collisions(
        terms
    )

    terms.sort(
        key=lambda item: (
            -int(
                item.get(
                    "priority"
                )
                or 0
            ),
            _key(
                str(
                    item.get(
                        "canonical"
                    )
                    or ""
                )
            ),
        )
    )

    output = dict(
        current_data
    )

    output[
        "terms"
    ] = terms

    metadata = dict(
        output.get(
            "metadata"
        )
        or {}
    )

    metadata[
        "merge_note"
    ] = (
        "Fusión segura para OCR/PLN: conserva "
        "términos actuales, recupera aliases del "
        "backup, incorpora términos enriquecidos "
        "y evita colisiones de aliases."
    )

    output[
        "metadata"
    ] = metadata

    TARGET.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "[OK] Backup de seguridad: "
        f"{SAFETY_BACKUP}"
    )

    print(
        "[OK] Diccionario actualizado: "
        f"{TARGET}"
    )

    print(
        "[OK] Total de términos: "
        f"{len(terms)}"
    )


if __name__ == "__main__":

    main()