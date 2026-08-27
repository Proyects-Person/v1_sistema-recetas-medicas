from pprint import pprint

from app.nlp.prescription_parser import (
    parse_prescription,
)


texto = """
Oxido de zinc 8%
Calamina 8%
Mentol 0.5%
Locion 100ml
Aplicar 2 veces al día durante 7 días
"""


resultado = parse_prescription(
    texto,
    ocr_confidence=0.90,
)


pprint(resultado)