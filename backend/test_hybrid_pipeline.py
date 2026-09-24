from pprint import pprint

from app.nlp.prescription_parser import (
    parse_prescription
)


TEST_CASES = {

    # ========================================================
    # RECETA 1
    # Urea + Ácido salicílico
    # ========================================================

    "RECETA_1": """
Unea3%
Acido salicilico2%
Crema 120g
Aplicar en zona afectada
2 veces al dia
""",


    # ========================================================
    # RECETA 2
    # Itraconazol + Terbinafina + Pramoxina
    # ========================================================

    "RECETA_2": """
Itraconazol 1% +
Terbinafina1% + Pramoxina5%
Crema120g
Aplicar en todas las lesiones
""",


    # ========================================================
    # RECETA 3
    # Isoconazol + Betametasona
    # ========================================================

    "RECETA_3": """
Isoconazoi1%
Betametazona2%
Crema c/p 30g
Aplicar mañana y noche
""",


    # ========================================================
    # RECETA 4
    # Ácido salicílico + Ácido láctico + Colodión
    # ========================================================

    "RECETA_4": """
Preparado dermatologico
Acido salicilico17%
Acido lactico17%
Base colodium csp 15ml
Aplicar 1 vez
""",


    # ========================================================
    # RECETA 5
    # Selenio + Minoxidil + Clobetasol
    # ========================================================

    "RECETA_5": """
Efluvio telogeno
Sulfito de selemio2,5%
Shampoo300g
Minoxidii2,5mg capsulas30
Minoxidil5% + Clobetasoi0,05%
Locion60ml
""",
}


def print_result(
    name: str,
    text: str,
) -> None:

    print(
        "\n"
        + "=" * 70
    )

    print(
        name
    )

    print(
        "=" * 70
    )


    result = (
        parse_prescription(

            text,

            ocr_confidence=0.90,
        )
    )


    print(
        "\n=== SALIDA VISIBLE ==="
    )

    print(
        "INSUMO + CONCENTRACIÓN"
    )


    pprint(
        result[
            "structured_rows"
        ]
    )


    print(
        "\n=== ESTADO NER ==="
    )

    print(
        result[
            "ner_status"
        ]
    )


    print(
        "\n=== CANDIDATOS DESCARTADOS ==="
    )

    pprint(
        result[
            "rejected_candidates"
        ]
    )


def main() -> None:

    for (
        name,
        sample,
    ) in TEST_CASES.items():

        print_result(
            name,
            sample
        )


if __name__ == "__main__":
    main()