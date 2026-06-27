"""
4º experimento: roda o Checador em notícias REAIS de fact-checking (Google Fact
Check / agências brasileiras), extraídas do JSON noticias_factcheck.json.

São alegações verificadas por agências (Aos Fatos, AFP, Estadão, etc.), em
português, recentes (2020-2024), com rótulo real/fake. Conjunto balanceado:
111 reais + 111 fakes.

LIMITAÇÃO IMPORTANTE (reportar no relatório): o "texto" de cada item é a
ALEGAÇÃO checada, não uma notícia completa no formato do Fake.br. São frases
mais curtas e de natureza diferente. Portanto, este teste avalia o Checador
fora do formato em que foi treinado — o resultado deve ser lido com essa
ressalva.

Uso:
    python -m scripts.testar_factcheck

Pré-requisitos:
    - Checador treinado.
    - Arquivo data/noticias_factcheck.json (gerado a partir do JSON original).
"""

import json
import sys
from pathlib import Path

from src import config
from src.agents.checador import Checador

ARQUIVO = Path("data/noticias_factcheck.json")


def main() -> None:
    if not config.TEM_MODELO:
        sys.exit("ERRO: Checador não treinado. Rode 'python -m scripts.treinar_checador'.")
    if not ARQUIVO.exists():
        sys.exit(f"ERRO: {ARQUIVO} não encontrado. Coloque o noticias_factcheck.json ali.")

    dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    checador = Checador()

    print(f"Testando o Checador em {len(dados)} notícias de fact-checking.\n")

    resultados = {"real": [], "fake": []}
    for item in dados:
        o = checador.prever(item["texto"])
        acertou = (o["classe"] == item["rotulo"])
        resultados[item["rotulo"]].append((acertou, o["prob_fake"]))

    print("=" * 52)
    print("DESEMPENHO DO CHECADOR EM NOTÍCIAS DE FACT-CHECKING")
    print("=" * 52)
    total_ac = 0
    total = 0
    for classe in ["real", "fake"]:
        res = resultados[classe]
        ac = sum(1 for a, _ in res if a)
        total_ac += ac
        total += len(res)
        prob_media = sum(p for _, p in res) / len(res) if res else 0
        print(f"  {classe:5}: {ac/len(res):5.1%} de acerto ({ac}/{len(res)})  "
              f"| prob_fake média: {prob_media:.0%}")
    print(f"\n  Acurácia geral: {total_ac/total:.1%} ({total_ac}/{total})")

    disse_fake = sum(1 for c in resultados.values() for a, p in c if p > 0.5)
    print(f"  Classificou como FAKE: {disse_fake}/{total} ({disse_fake/total:.0%})")
    print("=" * 52)
    print("\nLembre-se: o texto aqui são ALEGAÇÕES checadas, não notícias")
    print("completas — leia o resultado com essa ressalva no relatório.")


if __name__ == "__main__":
    main()