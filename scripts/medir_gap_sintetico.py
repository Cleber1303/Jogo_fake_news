"""
Experimento: mede o desempenho do Checador (Random Forest) em notícias
SINTÉTICAS geradas pelo Fofoqueiro (Gemini).

Responde à pergunta de pesquisa: um classificador treinado em texto humano
(Fake.br) mantém o desempenho diante de notícias geradas por LLM?

MELHORIAS desta versão:
  - Mostra o TÍTULO de cada notícia gerada, para você conferir, a olho, se o
    Fofoqueiro respeitou o pedido (real x fake). Transparência total.
  - Lote pequeno por vez (padrão 10) e pausa entre chamadas, para sofrer menos
    com a sobrecarga (503) do plano gratuito.
  - Salva o progresso a cada notícia (data/resultados_gap.json): é seguro
    interromper e continuar depois.
  - Resumo separa por classe — o número que conta a história é o acerto na
    classe REAL (se o Checador marca tudo como fake, esse cai).

Uso:
    python -m scripts.medir_gap_sintetico                 # gera 10 (5 real, 5 fake)
    python -m scripts.medir_gap_sintetico --n 20          # gera 20
    python -m scripts.medir_gap_sintetico --relatorio     # só o resumo do acumulado
    python -m scripts.medir_gap_sintetico --zerar         # apaga o acumulado e recomeça

Pré-requisitos: GOOGLE_API_KEY no .env e Checador treinado.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src import config
from src.agents.checador import Checador
from src.agents.fofoqueiro import Fofoqueiro

ARQUIVO = Path("data/resultados_gap.json")
TOPICOS = ["saúde", "política", "tecnologia", "economia",
           "ciência", "esportes", "meio ambiente", "educação"]


def carregar() -> list:
    if ARQUIVO.exists():
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    return []


def salvar(dados: list) -> None:
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                       encoding="utf-8")


def aviso_espera(segundos, tentativa):
    """Callback simples para mostrar no terminal quando estiver esperando a API."""
    print(f"      (API ocupada — aguardando {segundos:.0f}s, tentativa {tentativa})")


def coletar(n: int) -> None:
    if not config.TEM_API:
        sys.exit("ERRO: sem GOOGLE_API_KEY no .env.")
    if not config.TEM_MODELO:
        sys.exit("ERRO: Checador não treinado. Rode 'python -m scripts.treinar_checador'.")

    fofoqueiro = Fofoqueiro()
    checador = Checador()
    resultados = carregar()

    # Monta a lista de pedidos GARANTINDO metade real, metade fake.
    metade = n // 2
    pedidos = ["real"] * metade + ["fake"] * (n - metade)

    print(f"Gerando {n} notícias ({pedidos.count('real')} reais, "
          f"{pedidos.count('fake')} fakes). Já temos {len(resultados)} no total.\n")

    for i, veracidade in enumerate(pedidos):
        dificuldade = (i % 5) + 1
        topico = TOPICOS[i % len(TOPICOS)]

        try:
            m = fofoqueiro.gerar(topico, veracidade, dificuldade,
                                 on_espera=aviso_espera)
            saida = checador.prever(m.texto_completo)
        except Exception as e:
            print(f"  [{i+1}/{n}] FALHOU ({type(e).__name__}); pulando esta.\n")
            continue

        acertou = (saida["classe"] == veracidade)
        resultados.append({
            "gabarito": veracidade,
            "previsto": saida["classe"],
            "prob_fake": saida["prob_fake"],
            "dificuldade": dificuldade,
            "acertou": acertou,
            "titulo": m.titulo,
        })
        salvar(resultados)

        marca = "OK " if acertou else "ERRO"
        print(f"  [{i+1}/{n}] pedido={veracidade.upper():4} -> Checador disse "
              f"{saida['classe'].upper():4} [{marca}] (prob_fake {saida['prob_fake']:.0%})")
        print(f"           título: \"{m.titulo[:70]}\"")
        # pequena pausa para aliviar a pressão na API (reduz 503)
        time.sleep(1.5)

    print(f"\nConcluído. Total acumulado: {len(resultados)} notícias.")
    relatorio()


def relatorio() -> None:
    resultados = carregar()
    if not resultados:
        sys.exit("Nada coletado ainda.")

    total = len(resultados)
    acertos = sum(1 for r in resultados if r["acertou"])

    print("\n" + "=" * 52)
    print("DESEMPENHO DO CHECADOR EM NOTÍCIAS SINTÉTICAS (LLM)")
    print("=" * 52)
    print(f"Total de notícias: {total}")
    print(f"Acurácia geral   : {acertos/total:.1%} ({acertos}/{total})\n")

    print("Por classe (este é o dado que conta a história):")
    for classe in ["real", "fake"]:
        sub = [r for r in resultados if r["gabarito"] == classe]
        if sub:
            ac = sum(1 for r in sub if r["acertou"])
            print(f"  {classe:5}: {ac/len(sub):5.1%} de acerto ({ac}/{len(sub)})")

    # Quantas vezes o Checador disse "fake" no total (revela o viés)
    disse_fake = sum(1 for r in resultados if r["previsto"] == "fake")
    print(f"\nO Checador classificou como FAKE {disse_fake}/{total} "
          f"({disse_fake/total:.0%}) das notícias sintéticas.")

    print("\nPor dificuldade:")
    for d in range(1, 6):
        sub = [r for r in resultados if r["dificuldade"] == d]
        if sub:
            ac = sum(1 for r in sub if r["acertou"])
            print(f"  nível {d}: {ac/len(sub):.0%} ({ac}/{len(sub)})")
    print()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="quantas notícias gerar (padrão 10)")
    p.add_argument("--relatorio", action="store_true", help="só mostra o resumo")
    p.add_argument("--zerar", action="store_true", help="apaga o acumulado")
    args = p.parse_args()

    if args.zerar:
        if ARQUIVO.exists():
            ARQUIVO.unlink()
        print("Acumulado apagado.")
        return
    if args.relatorio:
        relatorio()
    else:
        coletar(args.n)


if __name__ == "__main__":
    main()