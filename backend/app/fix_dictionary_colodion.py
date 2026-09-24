from __future__ import annotations

import json

from pathlib import Path


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


DICTIONARIES_DIR = (
    BASE_DIR
    / "dictionaries"
)


FILES = [

    DICTIONARIES_DIR
    / "pharmaceutical_terms.json",

    DICTIONARIES_DIR
    / "pharmaceutical_ingredients_enriched.json",
]


ALIASES_TO_ADD = [

    "Colodium",

    "Base colodium",

    "Base colodion",

    "Base colodión",

    "Base colo",
]


def update_dictionary(
    path: Path,
) -> None:

    if not path.exists():

        print(
            f"[NO EXISTE] {path}"
        )

        return


    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


    terms = (
        data.get(
            "terms",
            []
        )
    )


    found = False


    for term in terms:

        if (
            str(
                term.get(
                    "canonical",
                    ""
                )
            ).strip().casefold()
            !=
            "colodión".casefold()
        ):

            continue


        found = True


        aliases = list(
            term.get(
                "aliases",
                []
            )
        )


        existing = {
            str(alias)
            .strip()
            .casefold()

            for alias
            in aliases
        }


        for alias in (
            ALIASES_TO_ADD
        ):

            if (
                alias.casefold()
                not in existing
            ):

                aliases.append(
                    alias
                )


        term[
            "aliases"
        ] = aliases


        # Ya estaba validado en tu diccionario.
        term[
            "verification"
        ] = "VERIFICADO"


        break


    if not found:

        terms.append(
            {
                "canonical":
                    "Colodión",

                "category":
                    "base",

                "priority":
                    100,

                "aliases":
                    ALIASES_TO_ADD,

                "verification":
                    "VERIFICADO",

                "observed_in_ner":
                    False,

                "observed_count":
                    0,

                "observed_strengths":
                    [],
            }
        )


    data[
        "terms"
    ] = terms


    path.write_text(

        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),

        encoding="utf-8",
    )


    print(
        f"[OK] {path.name}"
    )


def main() -> None:

    for path in FILES:

        update_dictionary(
            path
        )


if __name__ == "__main__":

    main()