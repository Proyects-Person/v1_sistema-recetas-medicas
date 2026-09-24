from __future__ import annotations

import json
import unicodedata

from pathlib import Path
from typing import Any


BASE_DIR = Path(
    __file__
).resolve().parent


DICTIONARIES_DIR = (
    BASE_DIR
    / "dictionaries"
)


TARGETS = [
    DICTIONARIES_DIR
    / "pharmaceutical_terms.json",

    DICTIONARIES_DIR
    / "pharmaceutical_ingredients_enriched.json",
]


NEW_VERSION = "2026-09-23.1"


# ============================================================
# NUEVOS TÉRMINOS Y VARIANTES OCR
# ============================================================

TERMS_TO_UPSERT: list[
    dict[str, Any]
] = [

    # --------------------------------------------------------
    # UREA
    # --------------------------------------------------------

    {
        "canonical":
            "Urea",

        "category":
            "principio_activo",

        "priority":
            109,

        "aliases": [
            "Unea",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "3%",
        ],
    },


    # --------------------------------------------------------
    # ÁCIDO SALICÍLICO
    # --------------------------------------------------------

    {
        "canonical":
            "Ácido salicílico",

        "category":
            "principio_activo",

        "priority":
            110,

        "aliases": [
            "Salicílico",
            "Acido salicilico",
            "Ácido salicilico",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "2%",
            "17%",
        ],
    },


    # --------------------------------------------------------
    # ITRACONAZOL
    # --------------------------------------------------------

    {
        "canonical":
            "Itraconazol",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Itraconazoi",
            "ItraconazoI",
            "Itraconaz0l",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "1%",
        ],
    },


    # --------------------------------------------------------
    # TERBINAFINA
    # --------------------------------------------------------

    {
        "canonical":
            "Terbinafina",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Terbinafína",
            "Terbinafma",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "1%",
        ],
    },


    # --------------------------------------------------------
    # PRAMOXINA
    # --------------------------------------------------------

    {
        "canonical":
            "Pramoxina",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Pramoxína",
            "Pramoxma",
            "Pramoxina HCl",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "5%",
        ],
    },


    # --------------------------------------------------------
    # ISOCONAZOL
    # --------------------------------------------------------

    {
        "canonical":
            "Isoconazol",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Isoconazoi",
            "lsoconazol",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "1%",
        ],
    },


    # --------------------------------------------------------
    # BETAMETASONA
    # --------------------------------------------------------

    {
        "canonical":
            "Betametasona",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Betametazona",
            "Betametasona",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "2%",
        ],
    },


    # --------------------------------------------------------
    # ÁCIDO LÁCTICO
    # --------------------------------------------------------

    {
        "canonical":
            "Ácido láctico",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Acido lactico",
            "Ácido lactico",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "17%",
        ],
    },


    # --------------------------------------------------------
    # COLODIÓN
    # --------------------------------------------------------

    {
        "canonical":
            "Colodión",

        "category":
            "base",

        "priority":
            90,

        "aliases": [
            "Colodium",
            "Colodion",
            "Base colodium",
            "Base colodion",
            "Base colodión",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [],
    },


    # --------------------------------------------------------
    # SULFITO DE SELENIO
    #
    # Se conserva tal como aparece en la muestra.
    # NO se transforma automáticamente en otro compuesto.
    # --------------------------------------------------------

    {
        "canonical":
            "Sulfito de selenio",

        "category":
            "principio_activo",

        "priority":
            108,

        "aliases": [
            "Sulfito selenio",
            "Sulfito de selénio",
            "Sulfito de selemio",
            "Sulfito de selenío",
        ],

        "verification":
            "PENDIENTE_VALIDACION_QF",

        "observed_strengths": [
            "2.5%",
        ],
    },


    # --------------------------------------------------------
    # MINOXIDIL
    # --------------------------------------------------------

    {
        "canonical":
            "Minoxidil",

        "category":
            "principio_activo",

        "priority":
            109,

        "aliases": [
            "Minoxidii",
            "Minoxidíl",
            "MinoxidiI",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "2.5 mg",
            "5%",
        ],
    },


    # --------------------------------------------------------
    # CLOBETASOL
    # --------------------------------------------------------

    {
        "canonical":
            "Clobetasol",

        "category":
            "principio_activo",

        "priority":
            110,

        "aliases": [
            "Clobetasoi",
            "Clobetazol",
            "Clobetas0l",
        ],

        "verification":
            "VERIFICADO",

        "observed_strengths": [
            "0.05%",
        ],
    },
]


# ============================================================
# NORMALIZACIÓN
# ============================================================

def _strip_accents(
    value: str,
) -> str:

    normalized = unicodedata.normalize(
        "NFD",
        value,
    )

    return "".join(
        char
        for char in normalized
        if unicodedata.category(
            char
        )
        != "Mn"
    )


def _key(
    value: str,
) -> str:

    return " ".join(
        _strip_accents(
            (
                value
                or ""
            ).casefold()
        ).split()
    )


# ============================================================
# UNIR LISTAS SIN DUPLICADOS
# ============================================================

def _merge_unique_strings(
    current: list[Any],
    incoming: list[Any],
) -> list[str]:

    result: list[str] = []

    seen: set[str] = set()


    for raw in [
        *current,
        *incoming,
    ]:

        value = str(
            raw
        ).strip()


        if not value:
            continue


        normalized_key = _key(
            value
        )


        if normalized_key in seen:
            continue


        seen.add(
            normalized_key
        )

        result.append(
            value
        )


    return result


# ============================================================
# INSERTAR O ACTUALIZAR TÉRMINOS
# ============================================================

def _upsert_terms(
    data: dict[str, Any],
) -> tuple[
    dict[str, Any],
    int,
    int,
]:

    terms = list(
        data.get(
            "terms",
            []
        )
    )


    index = {

        _key(
            str(
                item.get(
                    "canonical",
                    ""
                )
            )
        ):
            idx

        for idx, item
        in enumerate(
            terms
        )

        if str(
            item.get(
                "canonical",
                ""
            )
        ).strip()
    }


    added = 0

    updated = 0


    for incoming in TERMS_TO_UPSERT:

        canonical = str(
            incoming[
                "canonical"
            ]
        ).strip()


        normalized_key = _key(
            canonical
        )


        existing_idx = index.get(
            normalized_key
        )


        # ====================================================
        # TÉRMINO NUEVO
        # ====================================================

        if existing_idx is None:

            new_item = {

                "canonical":
                    canonical,

                "category":
                    incoming[
                        "category"
                    ],

                "priority":
                    int(
                        incoming.get(
                            "priority",
                            100
                        )
                    ),

                "aliases":
                    _merge_unique_strings(
                        [],
                        incoming.get(
                            "aliases",
                            []
                        )
                    ),

                "verification":
                    incoming.get(
                        "verification",
                        "PENDIENTE_VALIDACION_QF",
                    ),

                "observed_in_ner":
                    False,

                "observed_count":
                    0,

                "observed_strengths":
                    _merge_unique_strings(
                        [],
                        incoming.get(
                            "observed_strengths",
                            []
                        )
                    ),

                "source_note":
                    (
                        "Muestra manuscrita "
                        "incorporada 2026-09-23"
                    ),
            }


            terms.append(
                new_item
            )


            index[
                normalized_key
            ] = (
                len(terms)
                - 1
            )


            added += 1

            continue


        # ====================================================
        # ACTUALIZAR EXISTENTE
        # ====================================================

        current = dict(
            terms[
                existing_idx
            ]
        )


        current[
            "category"
        ] = incoming.get(

            "category",

            current.get(
                "category",
                "principio_activo",
            )
        )


        current[
            "priority"
        ] = max(

            int(
                current.get(
                    "priority",
                    50
                )
            ),

            int(
                incoming.get(
                    "priority",
                    50
                )
            )
        )


        current[
            "aliases"
        ] = _merge_unique_strings(

            list(
                current.get(
                    "aliases",
                    []
                )
            ),

            list(
                incoming.get(
                    "aliases",
                    []
                )
            )
        )


        current[
            "observed_strengths"
        ] = _merge_unique_strings(

            list(
                current.get(
                    "observed_strengths",
                    []
                )
            ),

            list(
                incoming.get(
                    "observed_strengths",
                    []
                )
            )
        )


        if not current.get(
            "verification"
        ):

            current[
                "verification"
            ] = incoming.get(

                "verification",

                "PENDIENTE_VALIDACION_QF",
            )


        terms[
            existing_idx
        ] = current


        updated += 1


    # ========================================================
    # ORDENAR
    # ========================================================

    terms.sort(

        key=lambda item: (

            -int(
                item.get(
                    "priority",
                    50
                )
            ),

            _key(
                str(
                    item.get(
                        "canonical",
                        ""
                    )
                )
            ),
        )
    )


    output = dict(
        data
    )


    output[
        "terms"
    ] = terms


    if "version" in output:

        output[
            "version"
        ] = NEW_VERSION


    metadata = dict(
        output.get(
            "metadata",
            {}
        )
    )


    metadata[
        "last_manual_expansion"
    ] = "2026-09-23"


    metadata[
        "last_manual_expansion_note"
    ] = (
        "Expansión para muestras manuscritas "
        "de dermatología: itraconazol, "
        "pramoxina, betametasona, sulfito "
        "de selenio y variantes OCR de "
        "insumos ya existentes."
    )


    output[
        "metadata"
    ] = metadata


    return (
        output,
        added,
        updated,
    )


# ============================================================
# EJECUCIÓN
# ============================================================

def main() -> None:

    for path in TARGETS:

        if not path.exists():

            print(
                f"[OMITIDO] No existe: {path}"
            )

            continue


        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )


        backup = path.with_name(
            (
                f"{path.stem}"
                ".before_2026_09_23"
                f"{path.suffix}"
            )
        )


        # ====================================================
        # BACKUP AUTOMÁTICO
        # ====================================================

        if not backup.exists():

            backup.write_text(

                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),

                encoding="utf-8",
            )


        output, added, updated = (
            _upsert_terms(
                data
            )
        )


        path.write_text(

            json.dumps(
                output,
                ensure_ascii=False,
                indent=2,
            ),

            encoding="utf-8",
        )


        print(
            f"[OK] {path.name}"
        )

        print(
            f"     agregados: {added}"
        )

        print(
            f"     actualizados: {updated}"
        )

        print(
            "     total términos: "
            f"{len(output.get('terms', []))}"
        )

        print(
            f"     backup: {backup.name}"
        )


if __name__ == "__main__":
    main()