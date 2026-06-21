# Caça à Fake News

Jogo educativo multiagente para combate à desinformação em língua portuguesa.
Projeto Final — INF 420 / INF 374 — UFV — 2026.1

Três agentes de IA interagem a cada rodada:

- **Fofoqueiro** (LLM / Gemini) — gera notícias novas (reais ou falsas), com título e fonte
- **Checador** (Random Forest + TF-IDF) — estima a credibilidade do texto
- **Juiz** (LLM / Gemini) — gera o feedback educativo a partir da saída do Checador, comparando jogador, detector e gabarito

A cada rodada o jogador lê a notícia, vota **real** ou **fake**, e — se achar que é fake — marca os indícios que percebeu. A pontuação recompensa não só o acerto, mas também a identificação correta dos sinais de desinformação.

## Arquitetura das técnicas de IA

O projeto aplica duas famílias distintas de IA, de forma complementar:

| Agente | Técnica | Papel |
| --- | --- | --- |
| Fofoqueiro | LLM (Gemini) via prompt estruturado | Gera as notícias parametrizadas por veracidade e dificuldade |
| Checador | Random Forest + TF-IDF (aprendizado supervisionado) | Classifica a veracidade e produz um score |
| Juiz | LLM (Gemini) no padrão LLM-as-a-Judge | Explica a rodada em linguagem natural, a partir da decisão do Checador |

O Checador é treinado sobre o corpus **Fake.br** com busca de hiperparâmetros (GridSearchCV) e validação cruzada, escolhendo a configuração de melhor F1-macro.

## Resultados do Checador

O Checador (Random Forest + TF-IDF), treinado no Fake.br com busca de
hiperparâmetros e validação cruzada de 5 folds, atinge no conjunto de teste:

| Métrica | Valor |
| --- | --- |
| F1-macro | 0.95 |
| AUC-ROC | 0.99 |
| Acurácia | 0.95 |

O desempenho está alinhado com a literatura para o Fake.br. O modelo é
ligeiramente mais cauteloso na classe real (recall 0.93) do que na fake
(recall 0.97), ou seja, na dúvida tende a sinalizar fake — comportamento
adequado para um detector de desinformação. Notícias sintéticas geradas pelo
Fofoqueiro com temas fora da distribuição do corpus de treino podem ser
classificadas incorretamente, ilustrando o gap entre detectores clássicos e
texto gerado por LLM.

## Como rodar no VSCode

```bash
# 1. Abra a pasta do projeto no VSCode

# 2. Crie e ative um ambiente virtual
python3 -m venv .venv
# Windows:        .venv\Scripts\activate
# Linux/macOS:    source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure a chave do Gemini
cp .env.example .env
# edite o .env e preencha GOOGLE_API_KEY

# 5. Baixe o corpus e treine o Checador (uma vez só)
#    (instruções de download em data/README.md)
python3 -m scripts.treinar_checador

# 6. Rode o jogo
streamlit run src/ui/app.py
```

Abre em `http://localhost:8501`.

> Dica: para testar só a lógica, sem interface: `python3 -m scripts.jogar_cli`

## Resiliência à cota da API

As notícias e o feedback são sempre gerados pelo Gemini em tempo real. Quando o
limite de requisições por minuto do plano gratuito é atingido (erro 429), o jogo
exibe um aviso de espera na tela e tenta novamente de forma automática, sem
interromper a partida.

## Estrutura

```
Jogo_fake_news/
├── src/
│   ├── config.py              # detecta chave e modelo disponíveis
│   ├── data/
│   │   ├── loader.py           # carrega o Fake.br (para o treino)
│   │   └── banco_demo.py       # notícias de exemplo (fallback offline)
│   ├── agents/
│   │   ├── fofoqueiro.py        # gerador de notícias (Gemini)
│   │   ├── checador.py          # classificador (Random Forest)
│   │   ├── juiz.py              # avaliador (Gemini, usa a saída do Checador)
│   │   └── gemini_utils.py      # retry com espera ao estourar a cota
│   ├── game/
│   │   ├── engine.py            # regras de rodada e pontuação
│   │   └── indicios.py          # detecção dos indícios para pontuar
│   └── ui/app.py                # interface Streamlit
├── scripts/
│   ├── treinar_checador.py      # treina o RF com GridSearch
│   └── jogar_cli.py             # joga uma rodada no terminal
├── data/                        # corpus (não versionado)
├── models/                      # modelos treinados (não versionado)
└── requirements.txt
```

## Pontuação

Por rodada: **+10** por acertar real/fake. Em notícias falsas, há um ajuste pelos
indícios marcados — **+3** por indício correto e **−2** por indício que não se
aplica (indícios que dependem de conhecimento de mundo são neutros e não punem).
A pontuação da rodada nunca fica abaixo de 10 quando o jogador acerta o veredito.

## Considerações éticas

O Fofoqueiro gera notícias falsas sintéticas com fins exclusivamente educativos.
As restrições no prompt impedem: citar pessoas reais, desinformação perigosa de
saúde, incitação a ódio ou violência, e uso de grupos vulneráveis.