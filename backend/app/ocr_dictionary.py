"""Postprocesamiento farmacéutico para OCR.

Este módulo NO entrena ni reemplaza al OCR. Toma el texto crudo devuelto por
Google Vision/EasyOCR y genera sugerencias con un diccionario farmacéutico.
Las sugerencias deben ser validadas por el químico farmacéutico.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DICTIONARY_PATH = BASE_DIR / "dictionaries" / "pharmaceutical_terms.json"

STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "y", "o", "a", "al", "en", "con",
    "para", "por", "un", "una", "uso", "dia", "día", "cada", "veces",
}

OCR_CONFUSIONS = {
    "0": "o",
    "1": "l",
    "5": "s",
    "8": "b",
    "@": "a",
    "€": "e",
}


@dataclass(frozen=True)
class DictionaryTerm:
    canonical: str
    category: str
    priority: int
    aliases: tuple[str, ...]

    @property
    def all_forms(self) -> tuple[str, ...]:
        return (self.canonical, *self.aliases)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_for_match(value: str) -> str:
    value = _strip_accents(value.lower())
    value = value.replace("º", "").replace("°", "")
    value = value.replace("/", " ").replace("-", " ")
    value = re.sub(r"[^a-z0-9%.,\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_token(value: str) -> str:
    value = normalize_for_match(value)
    if len(value) >= 4:
        value = "".join(OCR_CONFUSIONS.get(ch, ch) for ch in value)
    return value


def split_tokens(value: str) -> list[str]:
    return re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9%.,]+", value)


def load_dictionary() -> list[DictionaryTerm]:
    data = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    terms: list[DictionaryTerm] = []
    for item in data.get("terms", []):
        terms.append(
            DictionaryTerm(
                canonical=str(item["canonical"]),
                category=str(item.get("category", "termino")),
                priority=int(item.get("priority", 50)),
                aliases=tuple(str(v) for v in item.get("aliases", [])),
            )
        )
    # Más prioridad primero para resolver empates.
    terms.sort(key=lambda term: (-term.priority, term.canonical))
    return terms


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_for_match(a), normalize_for_match(b)).ratio()


def _window_candidates(tokens: list[str], min_size: int = 1, max_size: int = 4) -> list[tuple[int, int, str]]:
    candidates: list[tuple[int, int, str]] = []
    for start in range(len(tokens)):
        for size in range(min_size, max_size + 1):
            end = start + size
            if end <= len(tokens):
                text = " ".join(tokens[start:end])
                candidates.append((start, end, text))
    return candidates


def _suggestion_key(suggestion: dict[str, Any]) -> tuple[str, str]:
    return (suggestion.get("original", ""), suggestion.get("suggestion", ""))


def _format_percentage_spacing(text: str) -> str:
    text = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", r"\1%", text)
    text = re.sub(r"\b(\d+)\s+([.,])\s+(\d+)\b", r"\1\2\3", text)
    return text


def _apply_high_confidence_replacements(raw_text: str, suggestions: list[dict[str, Any]]) -> str:
    """Genera texto sugerido sin tocar el texto OCR original guardado.

    Solo aplica reemplazos cuando la confianza del diccionario es alta o cuando
    existe una regla contextual fuerte. El usuario siempre ve ambas versiones.
    """
    suggested = raw_text
    for item in suggestions:
        original = str(item.get("original", "")).strip()
        replacement = str(item.get("suggestion", "")).strip()
        confidence = float(item.get("confidence", 0))
        mode = item.get("mode", "")
        if not original or not replacement:
            continue
        if confidence < 0.78 and mode != "context_rule":
            continue
        pattern = re.compile(re.escape(original), flags=re.IGNORECASE)
        suggested = pattern.sub(replacement, suggested, count=1)
    return _format_percentage_spacing(suggested).strip()


def _context_rules(raw_text: str) -> list[dict[str, Any]]:
    normalized = normalize_for_match(raw_text)
    suggestions: list[dict[str, Any]] = []

    # Caso observado en las recetas enviadas: "Alcohol / Sonicado / 5%".
    # Google Vision puede confundir la b manuscrita de "boricado" con s.
    if "alcohol" in normalized:
        tokens = normalized.split()
        for token in tokens:
            score = max(similarity(token, target) for target in ["boricado", "boricad", "borico", "sonicado"])
            if token not in {"alcohol", "alc"} and score >= 0.66:
                percent = re.search(r"\d+(?:[.,]\d+)?\s*%", raw_text)
                replacement = "Alcohol boricado"
                if percent:
                    replacement = f"{replacement} {percent.group(0).replace(' ', '')}"
                original_text = raw_text.strip() if len(raw_text.strip()) <= 80 else token
                suggestions.append({
                    "original": original_text,
                    "suggestion": replacement,
                    "category": "principio_activo_preparado",
                    "confidence": round(max(score, 0.88), 2),
                    "reason": "Patrón contextual: aparece 'alcohol' y una palabra manuscrita muy parecida a 'boricado'.",
                    "mode": "context_rule",
                })
                break
    return suggestions


def analyze_ocr_text(raw_text: str, ocr_confidence: float = 0.0) -> dict[str, Any]:
    """Devuelve sugerencias farmacéuticas sin inventar texto OCR.

    raw_text: texto crudo del OCR.
    normalized_text: texto sugerido por diccionario. No sustituye al texto crudo.
    dictionary_suggestions: candidatos que el usuario debe validar.
    recognized_terms: términos reconocidos con coincidencia exacta o aproximada.
    """
    terms = load_dictionary()
    raw_text = (raw_text or "").strip()
    normalized_raw = normalize_for_match(raw_text)
    tokens_original = split_tokens(raw_text)
    tokens_norm = [normalize_token(token) for token in tokens_original]

    suggestions: list[dict[str, Any]] = []
    recognized: list[dict[str, Any]] = []

    # 1) Coincidencias exactas por forma canónica o alias.
    for term in terms:
        for form in term.all_forms:
            form_norm = normalize_for_match(form)
            if not form_norm or len(form_norm) < 2:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(form_norm)}(?![a-z0-9])", normalized_raw):
                recognized.append({
                    "term": term.canonical,
                    "category": term.category,
                    "match": form,
                    "confidence": 1.0,
                    "mode": "exact",
                })
                if form_norm != normalize_for_match(term.canonical) and form not in {"%", "g", "ml", "mL"}:
                    suggestions.append({
                        "original": form,
                        "suggestion": term.canonical,
                        "category": term.category,
                        "confidence": 1.0,
                        "reason": "Alias reconocido en el diccionario farmacéutico.",
                        "mode": "alias",
                    })
                break

    # 2) Reglas contextuales manuales de alta utilidad para recetas magistrales.
    suggestions.extend(_context_rules(raw_text))

    # 3) Coincidencias difusas por ventanas de palabras.
    windows = _window_candidates(tokens_original, 1, 4)
    for term in terms:
        canonical_norm = normalize_for_match(term.canonical)
        canonical_tokens = canonical_norm.split()
        if not canonical_norm or len(canonical_norm) < 4:
            continue

        best: tuple[float, str] = (0.0, "")
        for _, _, candidate in windows:
            candidate_norm = normalize_for_match(candidate)
            if not candidate_norm or candidate_norm in STOPWORDS:
                continue
            # Evita sugerir frases largas contra tokens demasiado cortos sin contexto.
            if len(candidate_norm) <= 3 and len(canonical_norm) > 5:
                continue
            # Tamaño aproximado de ventana para reducir falsos positivos.
            if abs(len(candidate_norm.split()) - len(canonical_tokens)) > 1:
                continue
            score = similarity(candidate_norm, canonical_norm)
            if score > best[0]:
                best = (score, candidate)

        threshold = 0.83 if len(canonical_tokens) == 1 else 0.76
        if term.category in {"unidad", "frecuencia", "indicacion"}:
            threshold = 0.90
        if best[0] >= threshold and normalize_for_match(best[1]) != canonical_norm:
            suggestions.append({
                "original": best[1],
                "suggestion": term.canonical,
                "category": term.category,
                "confidence": round(best[0], 2),
                "reason": "Coincidencia aproximada con el diccionario farmacéutico.",
                "mode": "fuzzy",
            })
            recognized.append({
                "term": term.canonical,
                "category": term.category,
                "match": best[1],
                "confidence": round(best[0], 2),
                "mode": "fuzzy",
            })

    # 4) Limpieza de duplicados, priorizando confianza y prioridad contextual.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for suggestion in suggestions:
        key = _suggestion_key(suggestion)
        if not key[0] or not key[1]:
            continue
        current = unique.get(key)
        if not current or float(suggestion.get("confidence", 0)) > float(current.get("confidence", 0)):
            unique[key] = suggestion
    suggestions_out = sorted(unique.values(), key=lambda item: float(item.get("confidence", 0)), reverse=True)[:12]

    recognized_unique: dict[str, dict[str, Any]] = {}
    for item in recognized:
        term = str(item.get("term", ""))
        if not term:
            continue
        current = recognized_unique.get(term)
        if not current or float(item.get("confidence", 0)) > float(current.get("confidence", 0)):
            recognized_unique[term] = item
    recognized_out = sorted(recognized_unique.values(), key=lambda item: (item.get("category", ""), item.get("term", "")))

    suggested_text = _apply_high_confidence_replacements(raw_text, suggestions_out) if suggestions_out else ""
    normalized_text = suggested_text if suggestions_out and suggested_text and suggested_text.strip() != raw_text.strip() else None
    return {
        "normalized_text": normalized_text,
        "dictionary_suggestions": suggestions_out,
        "recognized_terms": recognized_out,
        "dictionary_version": json.loads(DICTIONARY_PATH.read_text(encoding="utf-8")).get("version"),
        "warning": "Las sugerencias son apoyo de validación; no reemplazan el criterio del químico farmacéutico.",
    }
