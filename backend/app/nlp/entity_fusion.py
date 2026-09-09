from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from ..ocr_dictionary import analyze_ocr_text
from .ner_extractor import extract_ner_entities
from .regex_extractor import extract_regex_entities


COMPONENT_CATEGORIES = {
    "principio_activo",
    "principio_activo_preparado",
    "excipiente",
    "base_o_excipiente",
    "base",
    "extracto",
}

NOISE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:"
    r"cl[ií]nica|hospital|consultorio|centro\s+m[eé]dico|"
    r"dr\.?|dra\.?|doctor|doctora|cmp\b|ruc\b|"
    r"paciente\b|nombre\b|fecha\b|tel[eé]fono\b|celular\b|"
    r"direcci[oó]n\b|especialidad\b|firma\b|sello\b|"
    r"www\.|https?://|correo\b|email\b"
    r")",
    flags=re.IGNORECASE,
)


@dataclass
class Candidate:
    name: str
    start: int
    end: int
    dictionary_confidence: float = 0.0
    dictionary_mode: str | None = None
    statistical_ner: bool = False
    dictionary_ruler: bool = False
    concentration: str | None = None
    sources: set[str] = field(default_factory=set)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _simple_norm(value: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents((value or "").casefold())).strip()


def _find_span(line: str, value: str) -> tuple[int, int] | None:
    if not value:
        return None

    # Primero coincidencia literal, sin distinguir mayúsculas/minúsculas.
    match = re.search(re.escape(value), line, flags=re.IGNORECASE)
    if match:
        return match.start(), match.end()

    # Segundo intento tolerante a tildes. Mantiene longitud por carácter para
    # palabras españolas comunes, por lo que los offsets siguen siendo útiles.
    normalized_line = _strip_accents(line.casefold())
    normalized_value = _strip_accents(value.casefold())
    idx = normalized_line.find(normalized_value)
    if idx >= 0:
        return idx, idx + len(value)

    return None


def _line_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^\r\n]+", text):
        raw = match.group(0)
        leading = len(raw) - len(raw.lstrip())
        trailing_text = raw.strip()
        if not trailing_text:
            continue
        start = match.start() + leading
        end = start + len(trailing_text)
        spans.append((start, end, trailing_text))
    return spans


def _entities_for_line(
    entities: list[dict[str, Any]],
    line_start: int,
    line_end: int,
) -> list[dict[str, Any]]:
    result = []
    for ent in entities:
        if ent["start"] < line_end and ent["end"] > line_start:
            copy = dict(ent)
            copy["line_start"] = max(0, ent["start"] - line_start)
            copy["line_end"] = max(0, ent["end"] - line_start)
            result.append(copy)
    return result


def _ner_concentrations(line_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    concentrations: list[dict[str, Any]] = []
    units = [e for e in line_entities if e.get("label") == "UNIDAD"]

    for ent in line_entities:
        if ent.get("label") != "CONCENTRACION":
            continue

        value = str(ent.get("text", "")).strip().replace(",", ".")
        unit_text = ""
        nearest_distance = 999

        for unit in units:
            distance = int(unit["line_start"]) - int(ent["line_end"])
            if 0 <= distance <= 3 and distance < nearest_distance:
                unit_text = str(unit.get("text", "")).strip()
                nearest_distance = distance

        if unit_text == "%":
            normalized = f"{value}%"
        elif unit_text:
            normalized = f"{value} {unit_text}"
        else:
            normalized = value

        concentrations.append(
            {
                "normalized": normalized,
                "start": int(ent["line_start"]),
                "end": int(ent["line_end"]) + (len(unit_text) if unit_text else 0),
                "source": "ner",
            }
        )

    return concentrations


def _merge_candidates(candidates: list[Candidate]) -> list[Candidate]:
    merged: list[Candidate] = []

    for candidate in sorted(candidates, key=lambda c: (c.start, c.end)):
        target: Candidate | None = None
        for existing in merged:
            overlaps = candidate.start < existing.end and candidate.end > existing.start
            same_name = _simple_norm(candidate.name) == _simple_norm(existing.name)
            if overlaps or same_name:
                target = existing
                break

        if target is None:
            merged.append(candidate)
            continue

        # Preferir el nombre canónico proveniente del diccionario.
        if candidate.dictionary_confidence > target.dictionary_confidence:
            target.name = candidate.name
            target.start = candidate.start
            target.end = candidate.end
            target.dictionary_confidence = candidate.dictionary_confidence
            target.dictionary_mode = candidate.dictionary_mode

        target.statistical_ner = target.statistical_ner or candidate.statistical_ner
        target.dictionary_ruler = target.dictionary_ruler or candidate.dictionary_ruler
        target.sources.update(candidate.sources)

    return merged


def _pair_concentrations(
    candidates: list[Candidate],
    concentrations: list[dict[str, Any]],
) -> None:
    if not candidates or not concentrations:
        return

    available = set(range(len(concentrations)))

    # Emparejar primero por orden y cercanía hacia la derecha del insumo.
    for candidate in sorted(candidates, key=lambda c: c.start):
        best_index: int | None = None
        best_key: tuple[int, int] | None = None

        for idx in available:
            conc = concentrations[idx]
            c_start = int(conc.get("start", 0))
            distance = c_start - candidate.end
            is_after = 0 if distance >= -1 else 1
            absolute = abs(distance)
            key = (is_after, absolute)
            if best_key is None or key < best_key:
                best_key = key
                best_index = idx

        if best_index is not None:
            candidate.concentration = str(concentrations[best_index]["normalized"])
            candidate.sources.add(str(concentrations[best_index].get("source", "regex")))
            available.remove(best_index)


def _confidence(candidate: Candidate, noise_line: bool) -> float:
    score = 0.0

    if candidate.dictionary_confidence:
        if candidate.dictionary_mode == "exact":
            score += 0.50
        elif candidate.dictionary_mode == "fuzzy":
            score += 0.38
        else:
            score += 0.45
    elif candidate.dictionary_ruler:
        score += 0.45

    if candidate.statistical_ner:
        score += 0.35

    if candidate.concentration:
        score += 0.20

    if noise_line:
        score -= 0.35

    return max(0.0, min(1.0, round(score, 2)))


def fuse_ingredient_entities(
    text: str,
    ocr_confidence: float = 0.0,
) -> dict[str, Any]:
    """Fusiona NER + diccionario + regex y devuelve SOLO la salida de negocio.

    La forma farmacéutica, cantidad, frecuencia, etc. pueden seguir siendo
    analizadas por ``prescription_parser.py`` como contexto interno, pero esta
    función decide únicamente qué pares INSUMO/CONCENTRACION son suficientemente
    confiables para mostrar al químico farmacéutico.
    """

    text = (text or "").strip()
    ner_result = extract_ner_entities(text)
    ner_entities = ner_result["entities"]
    line_records: list[dict[str, Any]] = []

    for line_number, (line_start, line_end, line) in enumerate(_line_spans(text), start=1):
        line_entities = _entities_for_line(ner_entities, line_start, line_end)
        dictionary_result = analyze_ocr_text(line, ocr_confidence)
        regex_result = extract_regex_entities(line)

        concentrations = [
            {
                "normalized": item["normalized"],
                "start": item["start"],
                "end": item["end"],
                "source": "regex",
            }
            for item in regex_result.get("concentrations", [])
        ]

        if not concentrations:
            concentrations = _ner_concentrations(line_entities)

        candidates: list[Candidate] = []

        # Señal 1: diccionario farmacéutico/fuzzy matching.
        for item in dictionary_result.get("recognized_terms", []):
            if item.get("category") not in COMPONENT_CATEGORIES:
                continue

            match_text = str(item.get("match") or item.get("term") or "").strip()
            span = _find_span(line, match_text) or _find_span(line, str(item.get("term") or ""))
            if not span:
                continue

            candidates.append(
                Candidate(
                    name=str(item.get("term") or match_text),
                    start=span[0],
                    end=span[1],
                    dictionary_confidence=float(item.get("confidence") or 0.0),
                    dictionary_mode=str(item.get("mode") or ""),
                    sources={"dictionary"},
                )
            )

        # Señal 2: NER estadístico y EntityRuler farmacéutico.
        for ent in line_entities:
            if ent.get("label") != "INSUMO":
                continue

            source = str(ent.get("source") or "statistical_ner")
            name = str(ent.get("canonical") or ent.get("text") or "").strip()
            if not name:
                continue

            candidates.append(
                Candidate(
                    name=name,
                    start=int(ent["line_start"]),
                    end=int(ent["line_end"]),
                    statistical_ner=source == "statistical_ner",
                    dictionary_ruler=source == "dictionary_ruler",
                    sources={"ner" if source == "statistical_ner" else "dictionary_ruler"},
                )
            )

        candidates = _merge_candidates(candidates)
        _pair_concentrations(candidates, concentrations)

        line_records.append(
            {
                "line_number": line_number,
                "line": line,
                "noise": bool(NOISE_PREFIX_PATTERN.search(line)),
                "candidates": candidates,
                "concentrations": concentrations,
            }
        )

    # Caso frecuente: insumo en una línea y concentración sola en la siguiente.
    for idx, record in enumerate(line_records[:-1]):
        next_record = line_records[idx + 1]
        if len(record["candidates"]) != 1:
            continue
        candidate: Candidate = record["candidates"][0]
        if candidate.concentration:
            continue
        if next_record["candidates"]:
            continue
        if len(next_record["concentrations"]) == 1:
            candidate.concentration = str(next_record["concentrations"][0]["normalized"])
            candidate.sources.add(str(next_record["concentrations"][0].get("source", "regex")))

    ingredients: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for record in line_records:
        for candidate in record["candidates"]:
            dictionary_signal = bool(candidate.dictionary_confidence or candidate.dictionary_ruler)
            ner_signal = candidate.statistical_ner
            concentration_signal = bool(candidate.concentration)

            # Política conservadora anti-ruido:
            # 1) conocido por diccionario + concentración; o
            # 2) NER estadístico + concentración (permite nuevos insumos); o
            # 3) diccionario + NER aunque la concentración no sea legible.
            accepted = (
                (dictionary_signal and concentration_signal)
                or (ner_signal and concentration_signal)
                or (dictionary_signal and ner_signal)
            )

            if record["noise"] and not (dictionary_signal and ner_signal and concentration_signal):
                accepted = False

            confidence = _confidence(candidate, record["noise"])
            payload = {
                "ingredient": candidate.name,
                "concentration": candidate.concentration,
                "confidence": confidence,
                "sources": sorted(candidate.sources),
                "source_line": record["line"],
                "line_number": record["line_number"],
            }

            if accepted:
                ingredients.append(payload)
            else:
                rejected.append(payload)

    # Deduplicación conservando distintas concentraciones del mismo insumo.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in ingredients:
        key = (
            _simple_norm(str(item["ingredient"])),
            _simple_norm(str(item.get("concentration") or "")),
        )
        current = unique.get(key)
        if current is None or float(item["confidence"]) > float(current["confidence"]):
            unique[key] = item

    final_ingredients = sorted(unique.values(), key=lambda item: int(item["line_number"]))

    return {
        "ingredients": final_ingredients,
        "ner_entities": ner_entities,
        "ner_status": ner_result["status"],
        "rejected_candidates": rejected,
    }
