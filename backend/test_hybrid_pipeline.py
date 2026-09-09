from pprint import pprint

from app.nlp.prescription_parser import parse_prescription


SAMPLE = """CLÍNICA SAN PABLO
Dr. Juan Pérez CMP 12345
Paciente: María Fernández
Adapaleno 0.1%
Peróxido de benzoilo 2.5%
Gel 30 g
Firma y sello
"""

result = parse_prescription(SAMPLE, ocr_confidence=0.90)

print("\n=== SALIDA VISIBLE: INSUMO + CONCENTRACION ===")
pprint(result["structured_rows"])

print("\n=== ESTADO NER ===")
print(result["ner_status"])

print("\n=== CANDIDATOS DESCARTADOS ===")
pprint(result["rejected_candidates"])
