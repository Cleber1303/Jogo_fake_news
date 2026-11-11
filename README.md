# Caça à Fake News

Jogo educativo sobre desinformação em português. Projeto final de INF 420 /
INF 374, UFV, 2026.1.

A cada rodada o jogador lê uma notícia, vota real ou fake e, se votar fake, marca
os indícios que percebeu. A pontuação considera o veredito e os indícios.

Três agentes atuam na rodada:

| Agente | Técnica | Função |
| --- | --- | --- |
| Fofoqueiro | Gemini, com prompt estruturado | gera a notícia, real ou falsa, por veracidade e dificuldade |
| Checador | Random Forest + TF-IDF | classifica a notícia e produz um score de credibilidade |
| Juiz | Gemini, no padrão LLM-as-a-judge | explica a rodada a partir da saída do Checador, comparando jogador, detector e gabarito |

## Checador

Treinado no corpus Fake.br com GridSearchCV e validação cruzada de 5 folds,
escolhendo a configuração de melhor F1-macro. No conjunto de teste:

| Métrica | Valor |
| --- | --- |
| F1-macro | 0,95 |
| AUC-ROC | 0,99 |
| Acurácia | 0,95 |

O recall é 0,97 na classe fake e 0,93 na real: na dúvida, o modelo sinaliza fake.

Notícia sintética do Fofoqueiro com tema fora da distribuição do Fake.br costuma
ser classificada errado. É o gap entre detector clássico e texto gerado por LLM,
e aparece durante o jogo.

## Rodar

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # preencha GOOGLE_API_KEY

python3 -m scripts.treinar_checador    # uma vez só; corpus em data/README.md
streamlit run src/ui/app.py
```

Abre em http://localhost:8501. Sem interface: `python3 -m scripts.jogar_cli`.

Quando a cota por minuto do Gemini estoura (erro 429), o jogo avisa na tela e
tenta de novo sozinho, sem encerrar a partida.

## Pontuação

+10 por acertar real ou fake. Em notícia falsa, +3 por indício correto e −2 por
indício que não se aplica; indício que depende de conhecimento de mundo não pune.
Acertando o veredito, a rodada não fica abaixo de 10.

## Arquivos

```
src/
  config.py              detecta chave e modelo disponíveis
  data/loader.py         carrega o Fake.br para o treino
  data/banco_demo.py     notícias de exemplo, para rodar sem API
  agents/fofoqueiro.py   gerador de notícias
  agents/checador.py     classificador
  agents/juiz.py         avaliador, usa a saída do Checador
  agents/gemini_utils.py retry com espera quando a cota estoura
  game/engine.py         regras de rodada e pontuação
  game/indicios.py       detecção dos indícios
  ui/app.py              interface Streamlit
scripts/
  treinar_checador.py    treina o Random Forest com GridSearch
  jogar_cli.py           joga uma rodada no terminal
data/                    corpus, não versionado
models/                  modelos treinados, não versionados
```

## Ética

As notícias falsas são sintéticas e de uso educativo. O prompt proíbe citar
pessoa real, desinformação de saúde, incitação a ódio ou violência e uso de grupo
vulnerável.
