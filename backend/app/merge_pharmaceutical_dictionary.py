from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TARGET = BASE_DIR / "dictionaries" / "pharmaceutical_terms.json"
ENRICHED = BASE_DIR / "dictionaries" / "pharmaceutical_ingredients_enriched.json"

COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
    "insumo",
    "medicamento",
    "insumo/medicamento",
}

def _key(value: str) -> str:
    return " ".join((value or "").lower().strip().split())

def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"No existe el diccionario actual: {TARGET}")
    if not ENRICHED.exists():
        raise FileNotFoundError(f"No existe el diccionario enriquecido: {ENRICHED}")

    current = json.loads(TARGET.read_text(encoding="utf-8"))
    enriched = json.loads(ENRICHED.read_text(encoding="utf-8"))

    current_terms = current.get("terms", [])
    new_ingredients = enriched.get("terms", [])

    # Conserva formas farmacéuticas, vías y cualquier término estructural
    # que ya exista. Solo actualiza/agrega componentes farmacéuticos.
    preserved = [
        item for item in current_terms
        if str(item.get("category", "")) not in COMPONENT_CATEGORIES
    ]

    merged = preserved + new_ingredients
    merged.sort(
        key=lambda item: (
            -int(item.get("priority", 50)),
            _key(str(item.get("canonical", ""))),
        )
    )

    output = {
        **current,
        "metadata": {
            **current.get("metadata", {}),
            "ingredients_source": enriched.get("metadata", {}),
            "merge_note": (
                "Se conservaron formas/vías del diccionario previo y se "
                "actualizaron los componentes con los Excel del proyecto."
            ),
        },
        "terms": merged,
    }

    backup = TARGET.with_suffix(".backup.json")
    backup.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    TARGET.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Backup: {backup}")
    print(f"Diccionario actualizado: {TARGET}")
    print(f"Términos finales: {len(merged)}")

if __name__ == "__main__":
    main()
