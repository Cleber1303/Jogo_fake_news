"""
Configuração central do projeto.

Aqui detectamos automaticamente em que MODO o jogo deve rodar:

  - MODO COMPLETO: usa o Gemini (LLM real) e o Checador treinado (Random Forest).
    Requer GOOGLE_API_KEY no .env E o arquivo models/checador_rf.joblib.

  - MODO DEMO: usado quando falta a chave da API e/ou o modelo treinado.
    Os agentes usam *fallbacks* (banco de notícias de exemplo, heurística simples,
    feedback por template). Serve para rodar o jogo imediatamente, sem nenhuma
    configuração externa — ideal para testar a interface no VSCode.

A ideia é que o jogo SEMPRE rode. Conforme você configura a chave e treina o
modelo, ele migra sozinho do demo para o completo, sem mudar nenhum código.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (se existir) para o ambiente.
load_dotenv()

# Caminho do modelo treinado do Checador.
MODELO_CHECADOR = Path("models/checador_rf.joblib")

# Chave da API do Gemini (None se não configurada).
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Nome do modelo Gemini a usar quando em modo completo.
MODELO_GEMINI = "gemini-2.5-flash"  # 'flash' é mais rápido/barato; troque por '-pro' se quiser

# --- Flags de modo, calculadas uma vez na importação -------------------------

# Há chave de API válida? (consideramos válida se não for None nem o placeholder)
TEM_API = bool(GOOGLE_API_KEY) and GOOGLE_API_KEY != "cole_sua_chave_aqui"

# O modelo do Checador já foi treinado e salvo?
TEM_MODELO = MODELO_CHECADOR.exists()


def resumo_modo() -> str:
    """Retorna uma string legível com o estado atual da configuração."""
    linhas = [
        f"  Gemini (LLM)     : {'ATIVO' if TEM_API else 'demo (banco de exemplos)'}",
        f"  Checador treinado: {'ATIVO' if TEM_MODELO else 'demo (heurística)'}",
    ]
    return "\n".join(linhas)
