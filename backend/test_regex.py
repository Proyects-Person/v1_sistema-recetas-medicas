from pprint import pprint

from app.nlp.regex_extractor import extract_regex_entities


texto = """
Oxido de zinc 8%
Calamina 8%
Mentol 0.5%
Locion 100ml
Aplicar 2 veces al día durante 7 días
"""


resultado = extract_regex_entities(texto)

pprint(resultado)