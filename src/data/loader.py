"""
Carregamento do corpus Fake.br (usado só para treinar o Checador real).

Não é necessário para o modo demo do jogo.
"""

from pathlib import Path

import pandas as pd

FAKE_BR_PATH = Path("data/raw/Fake.br-Corpus/full_texts")


def carregar_fake_br(caminho: Path = FAKE_BR_PATH) -> pd.DataFrame:
    """
    Lê o corpus do disco e retorna um DataFrame com colunas:
        texto (str), label (int: 1=fake, 0=real), arquivo (str).

    Estrutura esperada:
        full_texts/true/*.txt
        full_texts/fake/*.txt
    """
    if not caminho.exists():
        raise FileNotFoundError(
            f"Corpus não encontrado em {caminho}. Veja data/README.md."
        )

    registros = []
    for rotulo in ["true", "fake"]:
        for arquivo in (caminho / rotulo).glob("*.txt"):
            registros.append({
                "texto": arquivo.read_text(encoding="utf-8").strip(),
                "label": 1 if rotulo == "fake" else 0,
                "arquivo": arquivo.name,
            })
    return pd.DataFrame(registros)


if __name__ == "__main__":
    df = carregar_fake_br()
    print(f"Total: {len(df)} notícias")
    print(df["label"].value_counts().rename({0: "real", 1: "fake"}))
