"""
Agente Fofoqueiro: gera as notícias do jogo (título + fonte + corpo).

Dois modos (escolhidos automaticamente, ver config.py):

  - COMPLETO: pede ao Gemini uma notícia em JSON (titulo, fonte, corpo),
    parametrizada por veracidade e dificuldade.
  - DEMO: sorteia uma notícia do banco de exemplos (src/data/banco_demo.py).

A interface pública é a mesma nos dois modos: .gerar(...) devolve sempre um
objeto ManchteGerada. Quem chama (o engine) não precisa saber o modo ativo.
"""

import json
import random
from dataclasses import dataclass
from typing import Optional

from src import config


@dataclass
class ManchteGerada:
    """Uma notícia gerada e seus metadados (o gabarito fica aqui)."""
    titulo: str
    fonte: Optional[str]   # None = notícia sem fonte declarada (isso é uma pista)
    corpo: str
    veracidade: str        # "real" ou "fake"  -> GABARITO da rodada
    dificuldade: int       # 1 a 5
    topico: str

    @property
    def fonte_exibida(self) -> str:
        """Texto da fonte para mostrar na tela (trata o caso de ausência)."""
        return self.fonte if self.fonte else "Fonte não informada"

    @property
    def texto_completo(self) -> str:
        """Junta título + corpo num texto único (é o que o Checador analisa)."""
        return f"{self.titulo}. {self.corpo}"


# Instrução de sistema usada apenas no modo COMPLETO (Gemini).
PROMPT_SISTEMA = """Você é o Fofoqueiro, gerador de notícias para um jogo \
educativo brasileiro de detecção de desinformação.

Você sempre responde com um objeto JSON com EXATAMENTE estas chaves:
  "titulo": a manchete (uma linha)
  "fonte" : quem teria publicado. Pode ser null se a notícia não tiver fonte.
  "corpo" : o texto da notícia (2 a 4 frases)

SE PEDIREM 'FAKE', gere desinformação plausível, MAS respeite os limites:
- Nunca cite nomes de pessoas reais.
- Nunca incite ódio ou violência.
- Nunca dê desinformação perigosa de saúde (vacinas, remédios, tratamentos).
- Nunca envolva crianças ou grupos vulneráveis em conteúdo prejudicial.
- Em fakes, a fonte pode ser null, vaga ("um amigo") ou um veículo inventado.

SE PEDIREM 'REAL', baseie-se em fatos gerais e plausíveis, tom jornalístico
sóbrio, e use uma fonte verificável (órgão público, instituto, universidade).

A DIFICULDADE controla quão sutil é a fake:
- 1: pistas óbvias (CAIXA-ALTA, !!!, "URGENTE", "BOMBA", apelo a compartilhar).
- 3: pistas moderadas (fonte vaga ou número solto).
- 5: nenhum marcador de superfície; o problema está só na factualidade.

Responda APENAS com o JSON, sem cercas de código, sem comentários."""


class Fofoqueiro:
    def __init__(self):
        self.modelo = None
        if config.TEM_API:
            import google.generativeai as genai
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.modelo = genai.GenerativeModel(
                config.MODELO_GEMINI, system_instruction=PROMPT_SISTEMA
            )

    def gerar(self, topico: str, veracidade: str, dificuldade: int) -> ManchteGerada:
        """Gera uma notícia (título + fonte + corpo)."""
        if self.modelo is not None:
            return self._gerar_via_gemini(topico, veracidade, dificuldade)
        return self._gerar_via_banco(veracidade)

    # ----------------------------- modo completo ----------------------------
    def _gerar_via_gemini(self, topico, veracidade, dificuldade) -> ManchteGerada:
        prompt = (
            f"Tópico: {topico}\n"
            f"Veracidade: {veracidade.upper()}\n"
            f"Dificuldade: {dificuldade}/5"
        )
        resposta = self.modelo.generate_content(prompt)
        dados = self._extrair_json(resposta.text)

        return ManchteGerada(
            titulo=dados.get("titulo", "(sem título)").strip(),
            fonte=(dados.get("fonte") or None),  # string vazia também vira None
            corpo=dados.get("corpo", "").strip(),
            veracidade=veracidade,
            dificuldade=dificuldade,
            topico=topico,
        )

    @staticmethod
    def _extrair_json(texto: str) -> dict:
        """
        Extrai o JSON da resposta do modelo.

        Às vezes o modelo embrulha o JSON em ```json ... ```; aqui limpamos
        essas cercas antes de fazer o parse. Se o parse falhar, devolvemos um
        dicionário mínimo para o jogo não quebrar.
        """
        limpo = texto.strip()
        if limpo.startswith("```"):
            # remove a primeira e a última linha de cerca de código
            linhas = [l for l in limpo.splitlines() if not l.strip().startswith("```")]
            limpo = "\n".join(linhas)
        try:
            return json.loads(limpo)
        except json.JSONDecodeError:
            return {"titulo": "(falha ao gerar)", "fonte": None, "corpo": limpo}

    # ------------------------------- modo demo ------------------------------
    def _gerar_via_banco(self, veracidade) -> ManchteGerada:
        from src.data.banco_demo import BANCO_NOTICIAS

        candidatos = [n for n in BANCO_NOTICIAS if n["veracidade"] == veracidade]
        if not candidatos:
            candidatos = BANCO_NOTICIAS

        n = random.choice(candidatos)
        return ManchteGerada(
            titulo=n["titulo"],
            fonte=n["fonte"],
            corpo=n["corpo"],
            veracidade=n["veracidade"],
            dificuldade=n["dificuldade"],
            topico=n["topico"],
        )
