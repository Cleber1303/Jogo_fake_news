"""
Diagnóstico completo do Checador: verifica se o treino está correto ou se o
desempenho alto no Fake.br vem de problema metodológico.

Faz três testes:
  1. VAZAMENTO: procura notícias duplicadas entre treino e teste. Se houver, o
     desempenho alto seria "trapaça" (o modelo viu a resposta).
  2. ATALHOS: mostra as palavras que mais pesam na decisão do modelo. Se forem
     nomes de veículos/datas (estilo), confirma que ele aprende distribuição, não
     veracidade — o que EXPLICA o gap (não é bug, é característica do dataset).
  3. OUTRA TÉCNICA: treina uma Regressão Logística (modelo bem diferente) no
     mesmo split. Se ela também acertar alto, o resultado NÃO é um defeito do
     Random Forest — é uma propriedade do problema/dataset.

Uso:
    python -m scripts.diagnosticar_checador

Pré-requisito: corpus Fake.br baixado.
"""

import sys
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from src.data.loader import carregar_fake_br


def normaliza(texto: str) -> str:
    """Normaliza para comparar duplicatas (minúsculas, espaços colapsados)."""
    return " ".join(texto.lower().split())


def teste_vazamento(X_tr, X_te) -> None:
    print("\n" + "=" * 56)
    print("TESTE 1 — VAZAMENTO (duplicatas entre treino e teste)")
    print("=" * 56)
    set_tr = {normaliza(t) for t in X_tr}
    dupes = [t for t in X_te if normaliza(t) in set_tr]
    print(f"Notícias de teste que também aparecem no treino: {len(dupes)}/{len(X_te)}")
    if len(dupes) == 0:
        print("RESULTADO: Sem vazamento. Treino e teste são disjuntos. ✓")
    else:
        print(f"ATENÇÃO: {len(dupes)} duplicatas — isso infla o desempenho!")


def teste_atalhos(X_tr, y_tr, n=20) -> None:
    print("\n" + "=" * 56)
    print("TESTE 2 — ATALHOS (palavras que mais pesam na decisão)")
    print("=" * 56)
    # Treina uma Logística simples só para ler os pesos (interpretável).
    vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 1), strip_accents="unicode")
    Xv = vec.fit_transform(X_tr)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(Xv, y_tr)

    nomes = vec.get_feature_names_out()
    coefs = clf.coef_[0]
    pares = sorted(zip(nomes, coefs), key=lambda p: p[1])

    print("\nPalavras que mais empurram para REAL (label 0):")
    for nome, c in pares[:n]:
        print(f"  {nome:20} {c:+.2f}")
    print("\nPalavras que mais empurram para FAKE (label 1):")
    for nome, c in pares[-n:][::-1]:
        print(f"  {nome:20} {c:+.2f}")
    print("\nLeia: se aparecerem nomes de veículos, datas ou termos de estilo")
    print("(não de conteúdo), o modelo aprende DISTRIBUIÇÃO, não veracidade —")
    print("o que explica o gap sem ser um erro de treino.")


def teste_outra_tecnica(X_tr, X_te, y_tr, y_te) -> None:
    print("\n" + "=" * 56)
    print("TESTE 3 — OUTRA TÉCNICA (Regressão Logística no mesmo split)")
    print("=" * 56)
    vec = TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                          min_df=2, sublinear_tf=True, strip_accents="unicode")
    Xtr = vec.fit_transform(X_tr)
    Xte = vec.transform(X_te)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(Xtr, y_tr)
    preds = clf.predict(Xte)
    f1 = f1_score(y_te, preds, average="macro")
    print(f"F1-macro da Regressão Logística: {f1:.3f}")
    print(f"(O Random Forest deu ~0.95 no mesmo corpus.)")
    print("\nLeia: se a Logística também der F1 alto (~0.9+), então o desempenho")
    print("não é um artefato do Random Forest — é uma propriedade do dataset.")
    print("Duas técnicas diferentes concordarem valida o resultado.")


def main() -> None:
    print("Carregando Fake.br...")
    df = carregar_fake_br()
    print(f"{len(df)} notícias.")

    # MESMO split do treino oficial.
    X_tr, X_te, y_tr, y_te = train_test_split(
        df["texto"].tolist(), df["label"].tolist(),
        test_size=0.2, stratify=df["label"], random_state=42,
    )

    teste_vazamento(X_tr, X_te)
    teste_atalhos(X_tr, y_tr)
    teste_outra_tecnica(X_tr, X_te, y_tr, y_te)

    print("\n" + "=" * 56)
    print("CONCLUSÃO DO DIAGNÓSTICO")
    print("=" * 56)
    print("Se: (1) sem vazamento, (2) atalhos de estilo nas palavras, e")
    print("(3) outra técnica também acerta alto, então o treino está CORRETO")
    print("e o gap em notícias sintéticas é um achado REAL (distribution shift),")
    print("não um erro de metodologia.")


if __name__ == "__main__":
    main()