"""
Agente Juiz: gera o feedback educativo ao final da rodada (LLM-as-a-Judge).

Dois modos (escolhidos automaticamente, ver config.py):

  - COMPLETO: o Gemini recebe a notícia (título, fonte, corpo), o gabarito, o
    voto e os indícios marcados, e escreve um feedback ESPECÍFICO daquela
    notícia — citando os sinais concretos presentes nela.
  - DEMO: monta um feedback por regras, mas também específico: inspeciona a
    própria notícia (tem fonte? tem caixa-alta? tem palavra de alerta?) e
    comenta o que encontrou. É menos fluido que o Gemini, mas já aponta os
    indícios reais daquela notícia.

Saída sempre em string (o texto do feedback).
"""

import json
from typing import List, Optional

from src import config
from src.agents.checador import PALAVRAS_ALERTA, extrair_features_superficie


PROMPT_SISTEMA = """Você é o Juiz, mediador de um jogo educativo brasileiro de \
detecção de fake news. Recebe os dados de uma rodada e dá um feedback curto e
ESPECÍFICO da notícia em questão.

REGRAS:
- 3 a 5 frases, em português claro e acessível (público geral, não acadêmico).
- Comece dizendo se o jogador acertou ou errou.
- Aponte os SINAIS CONCRETOS daquela notícia: comente o título, a fonte (se é
  confiável, vaga, inventada ou ausente) e o corpo. Cite trechos quando ajudar.
- Se o jogador marcou indícios, diga se foram pertinentes para ESTA notícia.
- Não invente dados que não estejam na notícia.
- Ao comentar o detector automático, baseie-se nos sinais que ele observou.
- Tom de mentor, sem sermão."""


class Juiz:
    def __init__(self):
        self.modelo = None
        if config.TEM_API:
            import google.generativeai as genai
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.modelo = genai.GenerativeModel(
                config.MODELO_GEMINI, system_instruction=PROMPT_SISTEMA
            )

    def avaliar(
        self,
        titulo: str,
        fonte: Optional[str],
        corpo: str,
        gabarito: str,
        voto_jogador: str,
        indicios_jogador: List[str],
        saida_checador: dict,
        on_espera=None,
    ) -> str:
        """Gera o feedback da rodada (string).

        Em modo completo, SEMPRE usa o Gemini. Se a quota estourar (429), espera
        e tenta de novo (retry). on_espera é o callback opcional para a UI avisar
        que está aguardando.
        """
        if self.modelo is not None:
            from src.agents.gemini_utils import chamar_com_retry
            return chamar_com_retry(
                self._avaliar_via_gemini,
                titulo, fonte, corpo, gabarito, voto_jogador,
                indicios_jogador, saida_checador,
                on_espera=on_espera,
            )
        return self._avaliar_via_template(
            titulo, fonte, corpo, gabarito, voto_jogador,
            indicios_jogador, saida_checador,
        )

    # ----------------------------- modo completo ----------------------------
    def _avaliar_via_gemini(
        self, titulo, fonte, corpo, gabarito, voto, indicios, checador
    ) -> str:
        contexto = {
            "noticia": {
                "titulo": titulo,
                "fonte": fonte or "(sem fonte declarada)",
                "corpo": corpo,
            },
            "gabarito": gabarito,
            "voto_jogador": voto,
            "indicios_marcados": indicios or ["(nenhum)"],
            "detector_automatico": {
                "classe": checador["classe"],
                "prob_fake": round(checador["prob_fake"], 2),
                # Sinais de superfície que o classificador observou — permite ao
                # Juiz explicar a decisão do Checador, não só repetir o número.
                "sinais_observados": checador.get("features_superficie", {}),
            },
        }
        prompt = (
            "Avalie a rodada a seguir e dê o feedback ao jogador. Cite os sinais "
            "concretos desta notícia e, ao comentar o detector automático, explique "
            "o resultado dele à luz dos 'sinais_observados'. Se o detector divergiu "
            "do gabarito, comente isso de forma educativa:\n\n"
            + json.dumps(contexto, ensure_ascii=False, indent=2)
        )
        return self.modelo.generate_content(prompt).text.strip()

    # ------------------------------- modo demo ------------------------------
    @staticmethod
    def _avaliar_via_template(
        titulo, fonte, corpo, gabarito, voto, indicios, checador
    ) -> str:
        """
        Feedback por regras, MAS específico desta notícia: inspeciona o texto
        em busca dos sinais reais e comenta os que encontrou.
        """
        acertou = voto == gabarito
        texto = f"{titulo}. {corpo}"
        feats = extrair_features_superficie(texto)
        texto_low = texto.lower()
        partes = []

        # 1) Acerto/erro.
        if acertou:
            partes.append("Boa! Você classificou corretamente.")
        else:
            partes.append(
                f"Dessa vez não foi: era **{gabarito}**, você marcou **{voto}**."
            )

        # 2) Sinais concretos encontrados NESTA notícia.
        sinais = []
        if not fonte:
            sinais.append("a notícia não informa nenhuma fonte")
        elif any(p in (fonte or "").lower() for p in ["amigo", "grupo", "whatsapp", "boato"]):
            sinais.append(f"a fonte é vaga ou pouco confiável (\"{fonte}\")")
        if feats["prop_caixa_alta"] > 0.15:
            sinais.append("há muito texto em CAIXA-ALTA, típico de alarme")
        alerta_encontradas = [p for p in PALAVRAS_ALERTA if p in texto_low]
        if alerta_encontradas:
            sinais.append(
                f"usa palavras de apelo como \"{alerta_encontradas[0]}\""
            )

        if sinais:
            partes.append("Nesta notícia: " + "; ".join(sinais) + ".")
        elif gabarito == "fake":
            partes.append(
                "Esta fake é sutil: não tem sinais óbvios de estilo, o problema "
                "está no conteúdo (ex.: dado sem contexto ou comparação distorcida)."
            )
        else:
            partes.append(
                "A notícia tem fonte identificável e tom sóbrio — sinais de "
                "conteúdo mais confiável."
            )

        # 3) Comentário sobre os indícios que o jogador marcou.
        if indicios:
            partes.append(f"Você apontou: {', '.join(indicios[:3])}.")

        # 4) Nota sobre o detector automático (e divergência, se houver).
        prob = checador["prob_fake"]
        if checador["classe"] != gabarito:
            partes.append(
                f"O detector automático se enganou aqui ({prob:.0%} de fake): "
                "fakes sutis costumam escapar de quem só olha o estilo do texto — "
                "por isso seu olhar humano importa."
            )
        else:
            partes.append(f"O detector automático concordou ({prob:.0%} de fake).")

        return " ".join(partes)