"""
Teste de CONTROLE: roda o Checador em notícias REAIS do próprio Fake.br.

Serve para comparar com o experimento das notícias sintéticas:
  - Se o Checador ACERTA as reais do Fake.br (diz "real" na maioria), mas ERRA
    as reais geradas por LLM (diz "fake"), então o problema NÃO é o Checador —
    é o texto sintético estar fora da distribuição de treino.
  - Isso isola a causa e valida o achado de pesquisa.

O script separa o teste em notícias que o modelo VIU no treino e notícias que
NÃO viu (conjunto de teste), usando o mesmo split do treino (random_state=42).
O número honesto é o desempenho nas notícias NÃO vistas.

Uso:
    python -m scripts.testar_checador_fakebr            # 30 reais + 30 fakes não vistas
    python -m scripts.testar_checador_fakebr --n 50     # 50 de cada

Pré-requisitos: corpus Fake.br baixado e Checador treinado.
"""

import argparse
import sys

from sklearn.model_selection import train_test_split

from src import config
from src.agents.checador import Checador
from src.data.loader import carregar_fake_br


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=30,
                   help="quantas notícias de cada classe testar (padrão 30)")
    p.add_argument("--mostrar", type=int, default=8,
                   help="quantos exemplos de títulos imprimir por classe")
    args = p.parse_args()

    if not config.TEM_MODELO:
        sys.exit("ERRO: Checador não treinado. Rode 'python -m scripts.treinar_checador'.")

    print("Carregando Fake.br...")
    df = carregar_fake_br()

    # Reproduz EXATAMENTE o split do treino, para separar o que o modelo
    # viu (treino) do que não viu (teste). Só o teste é avaliação honesta.
    X_tr, X_te, y_tr, y_te = train_test_split(
        df["texto"].tolist(), df["label"].tolist(),
        test_size=0.2, stratify=df["label"], random_state=42,
    )

    checador = Checador()

    # Pega n reais (label 0) e n fakes (label 1) do conjunto de TESTE.
    reais = [t for t, y in zip(X_te, y_te) if y == 0][:args.n]
    fakes = [t for t, y in zip(X_te, y_te) if y == 1][:args.n]

    print(f"\nTestando o Checador em notícias do Fake.br NÃO vistas no treino:")
    print(f"  {len(reais)} reais + {len(fakes)} fakes\n")

    resultados = {"real": [], "fake": []}

    for classe, textos in [("real", reais), ("fake", fakes)]:
        for txt in textos:
            o = checador.prever(txt)
            acertou = (o["classe"] == classe)
            resultados[classe].append((acertou, o["prob_fake"], txt))

    # Resumo
    print("=" * 52)
    print("DESEMPENHO DO CHECADOR EM NOTÍCIAS REAIS DO FAKE.BR")
    print("=" * 52)
    for classe in ["real", "fake"]:
        res = resultados[classe]
        ac = sum(1 for a, _, _ in res if a)
        print(f"  {classe:5}: {ac/len(res):5.1%} de acerto ({ac}/{len(res)})")

    # Mostra alguns exemplos de notícias REAIS e o que o Checador disse
    print(f"\nExemplos de notícias REAIS do Fake.br (primeiras {args.mostrar}):")
    for acertou, prob, txt in resultados["real"][:args.mostrar]:
        marca = "OK " if acertou else "ERRO"
        # primeira linha do texto como "título"
        titulo = txt.split("\n")[0][:65]
        print(f"  [{marca}] prob_fake={prob:.0%} | {titulo}")

    print("\n" + "=" * 52)
    print("COMPARAÇÃO (para o relatório):")
    print("  Reais do Fake.br  -> acerto alto  (modelo no domínio de treino)")
    print("  Reais geradas LLM -> acerto ~0%   (fora da distribuição)")
    print("  Essa diferença isola a causa no TEXTO SINTÉTICO, não no modelo.")
    print("=" * 52)


if __name__ == "__main__":
    main()