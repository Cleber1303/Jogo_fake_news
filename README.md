# Caça à Fake News

Jogo educativo multiagente para combate à desinformação em língua portuguesa.
Projeto Final — INF 420 / INF 374 — UFV — 2026.1

Três agentes interagem a cada rodada:

- **Fofoqueiro** (LLM / Gemini) — gera as manchetes (reais ou falsas)
- **Checador** (Random Forest + TF-IDF) — estima a credibilidade do texto
- **Juiz** (LLM / Gemini) — dá o feedback educativo comparando jogador, Checador e gabarito

## Roda em dois modos (automático)

| | Fofoqueiro | Checador | Precisa de quê? |
|---|---|---|---|
| **Demo** (padrão) | banco de notícias de exemplo | heurística de superfície | nada — só instalar e rodar |
| **Completo** | Gemini | Random Forest treinado | `GOOGLE_API_KEY` + modelo treinado |

O sistema detecta sozinho (em `src/config.py`) o que está disponível e migra
do demo para o completo sem mudar código. **Esta é uma implementação parcial:
o demo está 100% funcional; o modo completo já tem a estrutura pronta e é
ativado quando você configura a chave e treina o modelo.**

## Como rodar no VSCode

```bash
# 1. Abra a pasta caca-fake-news/ no VSCode

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# Windows:        .venv\Scripts\activate
# Linux/macOS:    source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o jogo (modo demo, sem configurar mais nada)
streamlit run src/ui/app.py
```

Abre em `http://localhost:8501`.

> Dica: se quiser testar só a lógica, sem interface:
> `python -m scripts.jogar_cli`

## Ativando o modo completo (depois)

1. **Gemini**: copie `.env.example` para `.env` e preencha `GOOGLE_API_KEY`.
2. **Checador real**: baixe o Fake.br (ver `data/README.md`) e rode
   `python -m scripts.treinar_checador`. Isso gera `models/checador_rf.joblib`.

Feito isso, reinicie o `streamlit` — o aviso de "modo demo" some.

## Estrutura

```
caca-fake-news/
├── src/
│   ├── config.py            # detecta demo vs completo
│   ├── data/
│   │   ├── loader.py         # carrega o Fake.br (treino)
│   │   └── banco_demo.py     # notícias de exemplo (modo demo)
│   ├── agents/
│   │   ├── fofoqueiro.py      # gerador (Gemini | banco)
│   │   ├── checador.py        # classificador (RF | heurística)
│   │   └── juiz.py            # avaliador (Gemini | template)
│   ├── game/engine.py         # regras de rodada e pontuação
│   └── ui/app.py              # interface Streamlit
├── scripts/
│   ├── treinar_checador.py    # treina o RF
│   └── jogar_cli.py           # joga uma rodada no terminal
├── data/                      # corpus (não versionado)
├── models/                    # modelos treinados
└── requirements.txt
```

## Considerações éticas

O Fofoqueiro gera notícias falsas sintéticas com fins educativos. As restrições
no prompt impedem: citar pessoas reais, desinformação perigosa de saúde,
incitação a ódio/violência, e uso de grupos vulneráveis.

## Status (parcial)

- [x] Estrutura completa do projeto
- [x] Modo demo funcional de ponta a ponta (jogo jogável sem configuração)
- [x] Interface Streamlit
- [x] Estrutura do modo completo (Gemini + RF) pronta para ativar
- [ ] Treino real do Checador no Fake.br *(rodar o script com o corpus)*
- [ ] BERTimbau, laço adversarial, métricas formais *(Fase 2)*
```
