"""
Joga uma rodada pelo terminal, sem interface — útil para testar a lógica
e os agentes rapidamente no VSCode.

Uso (a partir da raiz do projeto):
    python -m scripts.jogar_cli
"""

from src import config
from src.game.engine import Jogo


def main() -> None:
    print("=== Caça à Fake News (CLI) ===")
    print(config.resumo_modo())
    print()

    jogo = Jogo()
    rodada = jogo.nova_rodada()

    print("NOTÍCIA:")
    print("  TÍTULO:", rodada.manchete.titulo)
    print("  FONTE :", rodada.manchete.fonte_exibida)
    print("  CORPO :", rodada.manchete.corpo)
    print()

    voto = ""
    while voto not in ("real", "fake"):
        voto = input("Sua avaliação [real/fake]: ").strip().lower()

    jogo.finalizar_rodada(rodada, voto, indicios=[])

    print()
    print("--- Resultado ---")
    print(f"Gabarito: {rodada.manchete.veracidade}")
    print(f"Você {'ACERTOU' if rodada.acertou else 'errou'} "
          f"(+{rodada.pontos_ganhos} pts)")
    print(f"Checador: {rodada.saida_checador['classe']} "
          f"({rodada.saida_checador['prob_fake']:.0%} fake, "
          f"modo {rodada.saida_checador['modo']})")
    print()
    print("Feedback do Juiz:")
    print("  " + rodada.feedback_juiz)


if __name__ == "__main__":
    main()
