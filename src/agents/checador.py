"""
Agente Checador: estima a credibilidade de uma notícia.

Dois modos (escolhidos automaticamente, ver config.py):

  - COMPLETO: carrega o Random Forest treinado (models/checador_rf.joblib) e usa
    a probabilidade prevista pelo modelo.
  - DEMO: usa uma heurística simples baseada em features de superfície
    (caixa-alta, pontos de exclamação, palavras de alerta). Não é um classificador
    de verdade — é só para o jogo funcionar antes do treino.

Os dois modos devolvem o mesmo formato de saída, então o resto do sistema não
muda quando você treina o modelo de verdade.
"""

from pathlib import Path
from typing import Dict, List

from src import config

# Lista de marcadores lexicais associados a sensacionalismo/clickbait.
# Usada SÓ na heurística do modo demo.
PALAVRAS_ALERTA = [
    "urgente", "bomba", "compartilhe", "apaguem", "milagre", "segredo",
    "ninguém te conta", "antes que", "exclusivo", "chocante", "inacreditável",
]


def extrair_features_superficie(texto: str) -> Dict[str, float]:
    """
    Extrai indicadores interpretáveis de superfície linguística.

    Estas features são úteis tanto para a heurística do demo quanto para
    enriquecer o feedback ao jogador ("o texto tem 18% de letras em caixa-alta").
    """
    if not texto:
        return {
            "prop_caixa_alta": 0.0,
            "exclamacoes": 0.0,
            "palavras_alerta": 0.0,
        }

    letras = [c for c in texto if c.isalpha()]
    n_letras = max(len(letras), 1)
    n_palavras = max(len(texto.split()), 1)
    texto_low = texto.lower()

    return {
        # Proporção de letras maiúsculas (gritar no texto é típico de fake).
        "prop_caixa_alta": sum(1 for c in letras if c.isupper()) / n_letras,
        # Exclamações por palavra.
        "exclamacoes": texto.count("!") / n_palavras,
        # Quantas palavras de alerta aparecem, normalizado.
        "palavras_alerta": sum(texto_low.count(p) for p in PALAVRAS_ALERTA) / n_palavras,
    }


class Checador:
    def __init__(self, modelo_path: Path = config.MODELO_CHECADOR):
        self.modelo_path = modelo_path
        self.pipeline = None  # preenchido por .carregar() no modo completo

        # Se o modelo treinado existir, carrega. Senão, fica em modo heurístico.
        if config.TEM_MODELO:
            self.carregar()

    @property
    def modo_treinado(self) -> bool:
        return self.pipeline is not None

    def prever(self, texto: str) -> dict:
        """
        Avalia uma notícia e devolve:
            {
              "prob_fake": float em [0, 1],
              "classe": "fake" | "real",
              "modo": "treinado" | "heuristico",
              "features_superficie": {...}
            }
        """
        features = extrair_features_superficie(texto)

        if self.modo_treinado:
            prob_fake = float(self.pipeline.predict_proba([texto])[0][1])
            modo = "treinado"
        else:
            prob_fake = self._heuristica(features)
            modo = "heuristico"

        return {
            "prob_fake": prob_fake,
            "classe": "fake" if prob_fake > 0.5 else "real",
            "modo": modo,
            "features_superficie": features,
        }

    # ----------------------------- modo demo --------------------------------
    @staticmethod
    def _heuristica(features: Dict[str, float]) -> float:
        """
        Combina as features de superfície numa pseudo-probabilidade de fake.

        Pesos escolhidos à mão só para o demo ter um comportamento plausível:
        textos que gritam (caixa-alta), com muitas exclamações e palavras de
        alerta, recebem probabilidade alta de fake. NÃO é um modelo treinado.
        """
        score = (
            3.0 * features["prop_caixa_alta"]
            + 2.0 * features["exclamacoes"]
            + 5.0 * features["palavras_alerta"]
        )
        # Limita ao intervalo [0, 1].
        return max(0.0, min(1.0, score))

    # --------------------------- modo completo ------------------------------
    def treinar(self, textos: List[str], labels: List[int], pipeline=None) -> None:
        """Treina o Checador.

        Se um `pipeline` já configurado for passado (ex.: o melhor encontrado por
        busca de hiperparâmetros no script de treino), usa ele. Senão, monta um
        pipeline padrão TF-IDF + RandomForest com configuração reforçada.
        """
        if pipeline is not None:
            self.pipeline = pipeline
            self.pipeline.fit(textos, labels)
            return

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                max_features=10000,      # vocabulário maior
                ngram_range=(1, 2),      # palavras isoladas + pares
                min_df=2,                # ignora termos rraríssimos (ruído)
                sublinear_tf=True,       # suaviza contagens altas
                strip_accents="unicode", # "ÁGUA" e "agua" contam igual
            )),
            ("clf", RandomForestClassifier(
                n_estimators=400, n_jobs=-1, random_state=42,
                class_weight="balanced",
            )),
        ])
        self.pipeline.fit(textos, labels)

    def salvar(self) -> None:
        import joblib
        self.modelo_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, self.modelo_path)

    def carregar(self) -> None:
        import joblib
        self.pipeline = joblib.load(self.modelo_path)