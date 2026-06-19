"""
Lógica do jogo: orquestra os três agentes, mantém estado e pontuação.

Esta camada é independente da interface (Streamlit). Pode ser usada por um
script de linha de comando, por testes, ou pela UI — todos chamam os mesmos
métodos.

Fluxo de uma rodada:
    1. nova_rodada()      -> Fofoqueiro gera a manchete (gabarito fica escondido)
    2. [jogador vota e marca indícios na interface]
    3. finalizar_rodada() -> Checador analisa, Juiz dá feedback, calcula pontos
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional

from src.agents.checador import Checador
from src.agents.fofoqueiro import Fofoqueiro, ManchteGerada
from src.agents.juiz import Juiz

# Tópicos sorteados ao iniciar uma rodada (relevantes no modo completo/Gemini).
TOPICOS = [
    "saúde", "política", "tecnologia", "economia",
    "ciência", "esportes", "meio ambiente", "educação",
]


@dataclass
class Rodada:
    """Tudo o que aconteceu numa rodada — vai para o histórico."""
    manchete: ManchteGerada
    voto_jogador: Optional[str] = None
    indicios_jogador: List[str] = field(default_factory=list)
    saida_checador: Optional[dict] = None
    feedback_juiz: Optional[str] = None
    pontos_ganhos: int = 0
    acertou: bool = False


@dataclass
class EstadoJogo:
    """Placar acumulado da sessão."""
    pontuacao: int = 0
    rodadas_jogadas: int = 0
    acertos: int = 0
    historico: List[Rodada] = field(default_factory=list)


class Jogo:
    def __init__(
        self,
        fofoqueiro: Optional[Fofoqueiro] = None,
        checador: Optional[Checador] = None,
        juiz: Optional[Juiz] = None,
    ):
        # Permite injetar agentes (útil em testes); senão cria os padrão.
        self.fofoqueiro = fofoqueiro or Fofoqueiro()
        self.checador = checador or Checador()
        self.juiz = juiz or Juiz()
        self.estado = EstadoJogo()

    def nova_rodada(self, dificuldade: int = 2) -> Rodada:
        """Sorteia tópico e veracidade e pede a manchete ao Fofoqueiro."""
        topico = random.choice(TOPICOS)
        veracidade = random.choice(["real", "fake"])
        manchete = self.fofoqueiro.gerar(topico, veracidade, dificuldade)
        return Rodada(manchete=manchete)

    def finalizar_rodada(
        self, rodada: Rodada, voto: str, indicios: List[str]
    ) -> Rodada:
        """
        Recebe a decisão do jogador, roda Checador + Juiz, calcula a pontuação
        e atualiza o estado da sessão.

        Pontuação:
            +10 por acerto
            +2 por indício marcado (limitado a 5 indícios) — recompensa o
               jogador por justificar a desconfiança, não só por adivinhar.
        """
        rodada.voto_jogador = voto
        rodada.indicios_jogador = indicios

        # Checador analisa o texto completo (título + corpo).
        rodada.saida_checador = self.checador.prever(rodada.manchete.texto_completo)

        # Juiz produz o feedback educativo, recebendo a notícia estruturada.
        rodada.feedback_juiz = self.juiz.avaliar(
            titulo=rodada.manchete.titulo,
            fonte=rodada.manchete.fonte,
            corpo=rodada.manchete.corpo,
            gabarito=rodada.manchete.veracidade,
            voto_jogador=voto,
            indicios_jogador=indicios,
            saida_checador=rodada.saida_checador,
        )

        # Pontuação.
        rodada.acertou = (voto == rodada.manchete.veracidade)
        if rodada.acertou:
            rodada.pontos_ganhos = 10 + 2 * min(len(indicios), 5)
            self.estado.acertos += 1

        self.estado.pontuacao += rodada.pontos_ganhos
        self.estado.rodadas_jogadas += 1
        self.estado.historico.append(rodada)
        return rodada
