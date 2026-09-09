from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import spacy
from spacy.language import Language


NLP_DIR = Path(__file__).resolve().parent
APP_DIR = NLP_DIR.parent
DEFAULT_MODEL_PATH = NLP_DIR / "models" / "prescription_ner"
DICTIONARY_PATH = APP_DIR / "dictionaries" / "pharmaceutical_terms.json"

COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}

ALLOWED_LABELS = {
    "INSUMO",
    "CONCENTRACION",
    "UNIDAD",
    "FORMA_FARMACEUTICA",
    "CANTIDAD",
}


def _model_path() -> Path:
    configured = os.getenv("NER_MODEL_PATH", "").strip()
    return Path(configured) if configured else DEFAULT_MODEL_PATH


def _dictionary_patterns() -> list[dict[str, Any]]:
    if not DICTIONARY_PATH.exists():
        return []

    try:
        data = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    patterns: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in data.get("terms", []):
        category = str(item.get("category", "")).strip()
        if category not in COMPONENT_CATEGORIES:
            continue

        canonical = str(item.get("canonical", "")).strip()
        forms = [canonical, *[str(v).strip() for v in item.get("aliases", [])]]

        for form in forms:
            if not form:
                continue
            key = form.casefold()
            if key in seen:
                continue
            seen.add(key)
            patterns.append(
                {
                    "label": "INSUMO",
                    "pattern": form,
                    "id": f"dictionary::{canonical}",
                }
            )

    return patterns


def _add_dictionary_ruler(nlp: Language) -> None:
    name = "pharma_entity_ruler"
    if name in nlp.pipe_names:
        return

    config = {
        "overwrite_ents": False,
        "phrase_matcher_attr": "LOWER",
    }

    if "ner" in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", name=name, after="ner", config=config)
    else:
        ruler = nlp.add_pipe("entity_ruler", name=name, config=config)

    patterns = _dictionary_patterns()
    if patterns:
        ruler.add_patterns(patterns)


@lru_cache(maxsize=1)
def get_ner_pipeline() -> tuple[Language, str]:
    model_path = _model_path()

    if model_path.exists() and (model_path / "meta.json").exists():
        nlp = spacy.load(model_path)
        status = "statistical_ner+dictionary_ruler"
    else:
        # Fallback seguro: el proyecto sigue funcionando aunque aún no se haya
        # entrenado el modelo estadístico. El EntityRuler aprovecha el diccionario.
        nlp = spacy.blank("es")
        status = "dictionary_ruler_only"

    _add_dictionary_ruler(nlp)
    return nlp, status


def reload_ner_pipeline() -> None:
    """Limpia la caché después de entrenar/reemplazar el modelo."""
    get_ner_pipeline.cache_clear()


def extract_ner_entities(text: str) -> dict[str, Any]:
    text = text or ""
    nlp, status = get_ner_pipeline()
    doc = nlp(text)

    entities: list[dict[str, Any]] = []

    for ent in doc.ents:
        if ent.label_ not in ALLOWED_LABELS:
            continue

        canonical: str | None = None
        source = "statistical_ner"

        if ent.ent_id_.startswith("dictionary::"):
            source = "dictionary_ruler"
            canonical = ent.ent_id_.split("::", 1)[1] or None

        entities.append(
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "canonical": canonical,
                "source": source,
            }
        )

    return {
        "status": status,
        "model_path": str(_model_path()),
        "entities": entities,
    }
