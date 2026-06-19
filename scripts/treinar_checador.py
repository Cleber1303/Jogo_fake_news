"""
Treina o Checador (Random Forest) sobre o Fake.br e salva o modelo.

Uso (a partir da raiz do projeto):
    python -m scripts.treinar_checador

Pré-requisito: corpus baixado em data/raw/ (ver data/README.md).
Depois de rodar, o jogo passa automaticamente do modo heurístico para o treinado.
"""

from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split

from src.agents.checador import Checador
from src.data.loader import carregar_fake_br


def main() -> None:
    print("[1/4] Carregando Fake.br...")
    df = carregar_fake_br()
    print(f"      {len(df)} notícias.\n")

    print("[2/4] Split treino/teste (80/20, estratificado)...")
    X_tr, X_te, y_tr, y_te = train_test_split(
        df["texto"].tolist(), df["label"].tolist(),
        test_size=0.2, stratify=df["label"], random_state=42,
    )

    print("[3/4] Treinando Random Forest (pode levar alguns minutos)...")
    checador = Checador()
    checador.treinar(X_tr, y_tr)

    print("\n[4/4] Avaliação no teste:")
    preds = checador.pipeline.predict(X_te)
    print(classification_report(y_te, preds, target_names=["real", "fake"]))
    print(f"F1-macro: {f1_score(y_te, preds, average='macro'):.3f}\n")

    checador.salvar()
    print(f"Modelo salvo em {checador.modelo_path}")


if __name__ == "__main__":
    main()
