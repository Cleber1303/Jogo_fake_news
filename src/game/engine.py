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
    # Detalhamento da pontuação por indícios (preenchido só em fakes).
    indicios_corretos: List[str] = field(default_factory=list)   # marcou e era certo
    indicios_errados: List[str] = field(default_factory=list)    # marcou e não se aplica
    indicios_perdidos: List[str] = field(default_factory=list)   # eram certos e não marcou

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

    def nova_rodada(self, dificuldade: int = 2, on_espera=None) -> Rodada:
        """Sorteia tópico e veracidade e pede a manchete ao Fofoqueiro."""
        topico = random.choice(TOPICOS)
        veracidade = random.choice(["real", "fake"])
        manchete = self.fofoqueiro.gerar(topico, veracidade, dificuldade,
                                         on_espera=on_espera)
        return Rodada(manchete=manchete)

    def finalizar_rodada(
        self, rodada: Rodada, voto: str, indicios: List[str], on_espera=None
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
        # Regra base: +10 por acertar real/fake.
        # Para FAKES, há um ajuste pelos indícios marcados (ver abaixo).
        # Para REAIS, não há bônus/penalidade de indícios.
        rodada.acertou = (voto == rodada.manchete.veracidade)

        if rodada.acertou:
            pontos = 10
            self.estado.acertos += 1

            # Bônus de indícios só faz sentido quando a notícia é fake.
            if rodada.manchete.veracidade == "fake":
                from src.game.indicios import INDICIOS_NEUTROS, detectar_indicios

                corretos_possiveis = detectar_indicios(
                    rodada.manchete.titulo,
                    rodada.manchete.fonte,
                    rodada.manchete.corpo,
                )
                marcados = set(indicios)

                # Classifica cada marcação do jogador.
                acertos_ind = marcados & corretos_possiveis          # marcou certo
                # "errados" = marcou algo que não se aplica E que não é neutro
                # (indícios neutros não contam contra o jogador).
                errados_ind = {
                    i for i in (marcados - corretos_possiveis)
                    if i not in INDICIOS_NEUTROS
                }
                perdidos_ind = corretos_possiveis - marcados          # deixou passar

                rodada.indicios_corretos = sorted(acertos_ind)
                rodada.indicios_errados = sorted(errados_ind)
                rodada.indicios_perdidos = sorted(perdidos_ind)

                # +3 por indício correto, -2 por indício errado.
                # O bônus de indícios nunca derruba o ponto base do acerto:
                # garantimos que o total da rodada seja no mínimo 10.
                bonus = 3 * len(acertos_ind) - 2 * len(errados_ind)
                pontos = max(10, pontos + bonus)

            rodada.pontos_ganhos = pontos

        self.estado.pontuacao += rodada.pontos_ganhos
        self.estado.rodadas_jogadas += 1
        self.estado.historico.append(rodada)
        return rodada
