from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import spacy
from spacy.scorer import Scorer
from spacy.training import Example
from spacy.util import compounding, minibatch, compile_suffix_regex
from spacy.training import offsets_to_biluo_tags


HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "training" / "ner_training_data.json"
DEFAULT_OUTPUT = HERE / "models" / "prescription_ner"

# Ejemplos negativos sintéticos para que nombres, clínicas, teléfonos, firmas y
# encabezados no se aprendan como INSUMO solo por aparecer en una receta completa.
NEGATIVE_EXAMPLES = [
    "CLÍNICA DERMATOLÓGICA CENTRAL",
    "Hospital General - Dermatología",
    "Dr. Juan Pérez CMP 12345",
    "Dra. María López - Dermatología",
    "Paciente: Nombre Apellido",
    "Fecha: 31/08/2026",
    "Teléfono: 999999999",
    "Dirección: Av. Principal 123",
    "Firma y sello del médico",
    "RECETA MÉDICA",
    "Consultorio de Dermatología",
    "www.clinica-ejemplo.pe",
    "RUC 20123456789",
]


def load_data(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def configure_tokenizer(nlp) -> None:
    # El dataset separa ``5`` como CONCENTRACION y ``%`` como UNIDAD.
    # spaCy por defecto tokeniza ``5%`` como un solo token, así que añadimos
    # ``%`` como sufijo para respetar exactamente los offsets anotados.
    suffixes = list(nlp.Defaults.suffixes) + [r"%"]
    nlp.tokenizer.suffix_search = compile_suffix_regex(suffixes).search


def validate_alignment(nlp, records: list[dict]) -> None:
    invalid = []
    for record in records:
        entities = [
            (int(ent["start"]), int(ent["end"]), str(ent["label"]))
            for ent in record.get("entities", [])
        ]
        tags = offsets_to_biluo_tags(nlp.make_doc(record["text"]), entities)
        if "-" in tags:
            invalid.append(record.get("formula_id", "sin_id"))
    if invalid:
        raise ValueError(
            "Hay entidades que no coinciden con los límites de token de spaCy: "
            + ", ".join(invalid[:10])
        )


def as_examples(nlp, records: list[dict]) -> list[Example]:
    examples: list[Example] = []
    for record in records:
        entities = [
            (int(ent["start"]), int(ent["end"]), str(ent["label"]))
            for ent in record.get("entities", [])
        ]
        examples.append(Example.from_dict(nlp.make_doc(record["text"]), {"entities": entities}))
    return examples


def evaluate(nlp, records: list[dict]) -> dict:
    scorer = Scorer()
    examples = []
    for record in records:
        reference = Example.from_dict(
            nlp.make_doc(record["text"]),
            {
                "entities": [
                    (int(ent["start"]), int(ent["end"]), str(ent["label"]))
                    for ent in record.get("entities", [])
                ]
            },
        ).reference
        predicted = nlp(record["text"])
        examples.append(Example(predicted, reference))
    scores = scorer.score(examples)
    return {
        "ents_p": round(float(scores.get("ents_p", 0.0)), 4),
        "ents_r": round(float(scores.get("ents_r", 0.0)), 4),
        "ents_f": round(float(scores.get("ents_f", 0.0)), 4),
        "ents_per_type": scores.get("ents_per_type", {}),
    }


def train(data_path: Path, output_path: Path, epochs: int, dev_fold: int, train_all: bool) -> None:
    random.seed(42)
    records = load_data(data_path)

    if train_all:
        train_records = list(records)
        dev_records: list[dict] = []
    else:
        train_records = [r for r in records if int(r.get("fold_cv", 0)) != dev_fold]
        dev_records = [r for r in records if int(r.get("fold_cv", 0)) == dev_fold]

    # Negativos solo al entrenamiento.
    train_records.extend(
        {
            "text": text,
            "entities": [],
            "formula_id": f"NEG-{idx:02d}",
            "fold_cv": 0,
        }
        for idx, text in enumerate(NEGATIVE_EXAMPLES, start=1)
    )

    nlp = spacy.blank("es")
    configure_tokenizer(nlp)
    validate_alignment(nlp, records)
    ner = nlp.add_pipe("ner")

    labels = sorted({ent["label"] for record in records for ent in record.get("entities", [])})
    for label in labels:
        ner.add_label(label)

    train_examples = as_examples(nlp, train_records)
    optimizer = nlp.initialize(lambda: train_examples)

    for epoch in range(1, epochs + 1):
        random.shuffle(train_examples)
        losses = {}
        batches = minibatch(train_examples, size=compounding(4.0, 16.0, 1.001))
        for batch in batches:
            nlp.update(batch, sgd=optimizer, drop=0.25, losses=losses)

        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"epoch={epoch:03d} loss={losses.get('ner', 0.0):.4f}")

    output_path.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_path)

    report = {
        "training_examples": len(train_records),
        "development_examples": len(dev_records),
        "labels": labels,
        "epochs": epochs,
        "dev_fold": None if train_all else dev_fold,
        "train_all": train_all,
    }

    if dev_records:
        report["evaluation"] = evaluate(nlp, dev_records)

    (output_path / "training_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Modelo guardado en: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--dev-fold", type=int, default=5, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--train-all", action="store_true")
    args = parser.parse_args()

    train(args.data, args.output, args.epochs, args.dev_fold, args.train_all)
