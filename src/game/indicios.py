"""
Detecção automática de indícios de fake news em uma notícia.

Dado o título, a fonte e o corpo, decide quais checkboxes (indícios) DEVERIAM
ter sido marcadas pelo jogador. É o "gabarito de indícios" usado para pontuar.

IMPORTANTE — três categorias de indício:
  - DETECTÁVEIS: regras de superfície conseguem decidir com confiança
    (ex.: ausência de fonte, caixa-alta, apelo a compartilhar).
  - NEUTROS: dependem de conhecimento de mundo ou de análise semântica que
    regras simples não fazem (ex.: "contradiz o que eu já sabia"). Não entram
    no gabarito: marcá-los não soma nem subtrai ponto. Assim o jogador nunca é
    punido por um indício que o sistema não tem como avaliar.

Cada string aqui é IDÊNTICA ao texto da checkbox em src/ui/app.py — é o que
liga a detecção à interface.
"""

import re

# Palavras de apelo/urgência típicas de desinformação.
PALAVRAS_APELO = [
    "urgente", "bomba", "compartilhe", "compartilhar", "antes que apaguem",
    "apaguem", "corre", "não perca", "milagre", "segredo", "exclusivo",
    "chocante", "inacreditável", "ninguém conta", "não quer que você",
]

# Termos que sugerem fonte vaga/anedótica (não institucional).
FONTE_VAGA = ["amigo", "grupo", "whatsapp", "boato", "ouvi dizer", "dizem que"]

# Indícios que NENHUMA regra simples consegue julgar com segurança.
# Ficam de fora do gabarito (tratados como neutros na pontuação).
INDICIOS_NEUTROS = {
    "Contradiz coisas que eu já sabia",
    "Números soltos, sem contexto",
    "Manchete promete uma coisa, texto entrega outra",
    "Erros de português ou redação ruim",
    "Insinua que estão escondendo a verdade",
}


def detectar_indicios(titulo: str, fonte, corpo: str) -> set:
    """
    Retorna o CONJUNTO de indícios (strings) que a notícia realmente apresenta,
    considerando só os detectáveis por regra. Os textos batem exatamente com as
    checkboxes da interface.
    """
    texto = f"{titulo}. {corpo}"
    texto_low = texto.lower()
    fonte_low = (fonte or "").lower()
    detectados = set()

    # --- Grupo: De onde vem a informação? ---
    if not fonte:
        detectados.add("Não diz quem é a fonte")
    if fonte and any(v in fonte_low for v in FONTE_VAGA):
        # Fonte existe mas é vaga/pessoal -> "site/jornal que não conheço".
        detectados.add("Site ou jornal que eu não conheço")
    if "especialista" in texto_low and not fonte:
        detectados.add("'Especialista' ou órgão que parece inventado")

    # --- Grupo: Como soa o texto? ---
    letras = [c for c in texto if c.isalpha()]
    if letras:
        prop_caixa = sum(1 for c in letras if c.isupper()) / len(letras)
        if prop_caixa > 0.12 or texto.count("!") >= 2:
            detectados.add("Tom exagerado ou dramático demais")
            detectados.add("Tenta provocar raiva, medo ou indignação")

    # --- Grupo: Está tentando me convencer demais? ---
    if any(p in texto_low for p in PALAVRAS_APELO):
        detectados.add("Pede pra compartilhar com urgência")

    # --- Grupo: faz sentido? (parte detectável) ---
    # "Falta data/local/contexto": aproximação — fake costuma não trazer data.
    tem_data = bool(re.search(r"\b\d{1,2}\s+de\s+\w+|\bdiário oficial\b|\bedital\b", texto_low))
    if not fonte and not tem_data:
        detectados.add("Falta data, local ou contexto")

    return detectados