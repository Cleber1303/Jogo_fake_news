"""
Treina o Checador (Random Forest) sobre o Fake.br, com busca de hiperparâmetros,
e salva o melhor modelo encontrado.

Uso (a partir da raiz do projeto):
    python -m scripts.treinar_checador

Pré-requisito: corpus baixado em data/raw/ (ver data/README.md).
Depois de rodar, o jogo passa automaticamente do modo heurístico para o treinado.

O que este script faz para deixar o modelo "o mais treinado possível":
  1. TF-IDF reforçado (uni+bigramas, 10k features, min_df, sublinear_tf, sem acento).
  2. GridSearchCV: testa combinações de hiperparâmetros do Random Forest com
     validação cruzada (5 folds), escolhendo a de melhor F1-macro.
  3. Reporta métricas no conjunto de teste (que o modelo nunca viu no treino).
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline

from src.agents.checador import Checador
from src.data.loader import carregar_fake_br


def main() -> None:
    print("[1/5] Carregando Fake.br...")
    df = carregar_fake_br()
    print(f"      {len(df)} notícias.\n")

    print("[2/5] Split treino/teste (80/20, estratificado)...")
    X_tr, X_te, y_tr, y_te = train_test_split(
        df["texto"].tolist(), df["label"].tolist(),
        test_size=0.2, stratify=df["label"], random_state=42,
    )

    # Pipeline base: TF-IDF reforçado + Random Forest.
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, sublinear_tf=True,
            strip_accents="unicode",
        )),
        ("clf", RandomForestClassifier(
            n_jobs=-1, random_state=42, class_weight="balanced",
        )),
    ])

    # Espaço de busca dos hiperparâmetros. Ajuste se quiser uma busca mais ampla
    # (mais combinações = mais lento, mas potencialmente melhor).
    grade = {
        "tfidf__max_features": [5000, 10000],
        "clf__n_estimators": [300, 500],
        "clf__max_depth": [None, 60],
        "clf__min_samples_leaf": [1, 2],
    }

    print("[3/5] Busca de hiperparâmetros (GridSearchCV, 5 folds)...")
    print("      Isso testa várias combinações — pode levar vários minutos.\n")
    busca = GridSearchCV(
        pipeline, grade, scoring="f1_macro", cv=5, n_jobs=-1, verbose=1,
    )
    busca.fit(X_tr, y_tr)

    print(f"\n      Melhor F1-macro (validação cruzada): {busca.best_score_:.3f}")
    print(f"      Melhores parâmetros: {busca.best_params_}\n")

    print("[4/5] Avaliação no conjunto de teste (nunca visto):")
    melhor = busca.best_estimator_
    preds = melhor.predict(X_te)
    probs = melhor.predict_proba(X_te)[:, 1]
    print(classification_report(y_te, preds, target_names=["real", "fake"]))
    print(f"F1-macro: {f1_score(y_te, preds, average='macro'):.3f}")
    print(f"AUC-ROC : {roc_auc_score(y_te, probs):.3f}\n")

    print("[5/5] Salvando o melhor modelo...")
    checador = Checador()
    # Reaproveita o melhor pipeline já treinado (não re-treina do zero).
    checador.pipeline = melhor
    checador.salvar()
    print(f"Modelo salvo em {checador.modelo_path}")


if __name__ == "__main__":
    main()