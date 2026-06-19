"""
Interface do jogo Caça à Fake News (Streamlit).

Como rodar (a partir da RAIZ do projeto, a pasta caca-fake-news/):

    streamlit run src/ui/app.py

Abre uma aba no navegador (geralmente http://localhost:8501).

Sobre o session_state do Streamlit:
    O Streamlit re-executa este arquivo inteiro a cada interação (clique,
    checkbox, etc.). Para não perder o estado do jogo entre essas re-execuções,
    guardamos tudo em st.session_state, que persiste durante a sessão.
"""

import streamlit as st

# --- garante que a raiz do projeto esteja no path, venha de onde vier ---
# O Streamlit executa este arquivo de dentro de src/ui/, então sem isto o
# Python não encontra o pacote 'src'. Subimos 2 níveis (ui -> src -> raiz).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# ------------------------------------------------------------------------

from src import config
from src.game.engine import Jogo


# ---------------------------------------------------------------------------
# Grupos de indícios mostrados quando o jogador vota "Fake".
# Os títulos são as PERGUNTAS mentais que a pessoa faz ao desconfiar — mais
# intuitivo para o público geral do que rótulos técnicos.
# ---------------------------------------------------------------------------
INDICIOS = {
    "Como soa o texto?": [
        "Tom exagerado ou dramático demais",
        "Tenta provocar raiva, medo ou indignação",
        "Erros de português ou redação ruim",
    ],
    "De onde vem essa informação?": [
        "Não diz quem é a fonte",
        "Site ou jornal que eu não conheço",
        "'Especialista' ou órgão que parece inventado",
    ],
    "O que está sendo dito faz sentido?": [
        "Números soltos, sem contexto",
        "Contradiz coisas que eu já sabia",
        "Manchete promete uma coisa, texto entrega outra",
        "Falta data, local ou contexto",
    ],
    "Está tentando me convencer demais?": [
        "Insinua que estão escondendo a verdade",
        "Pede pra compartilhar com urgência",
    ],
}


# CSS mínimo só para a notícia ganhar destaque de "card".
# IMPORTANTE: fixamos tanto o fundo quanto a cor do texto (color: #1a1a1a).
# Sem fixar a cor, no tema ESCURO o Streamlit deixa o texto branco — e branco
# sobre fundo claro fica invisível. Fixando os dois, o card fica legível nos
# temas claro e escuro.
CSS = """
<style>
.bloco-noticia {
    background: #f6f8fa;
    color: #1a1a1a;
    border-left: 4px solid #2e7d9a;
    border-radius: 6px;
    padding: 18px 20px;
    margin: 8px 0 4px 0;
}
.noticia-titulo {
    font-size: 1.2rem;
    font-weight: 700;
    line-height: 1.35;
    margin-bottom: 6px;
}
.noticia-fonte {
    font-size: 0.85rem;
    font-style: italic;
    color: #5a6470;
    margin-bottom: 10px;
}
.noticia-corpo {
    font-size: 1.02rem;
    line-height: 1.5;
}
</style>
"""


@st.cache_resource
def carregar_jogo() -> Jogo:
    """
    Cria o jogo uma única vez por sessão.

    @st.cache_resource garante que os agentes (e o carregamento do modelo) não
    sejam recriados a cada re-execução do script.
    """
    return Jogo()


def iniciar_estado() -> None:
    """Inicializa as chaves do session_state na primeira execução."""
    if "jogo" not in st.session_state:
        st.session_state.jogo = carregar_jogo()
        st.session_state.rodada = None            # rodada atual
        st.session_state.fase = "inicio"          # inicio | jogando | feedback


def barra_status(jogo: Jogo) -> None:
    """Mostra pontos, número de rodadas e acertos no topo."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Pontos", jogo.estado.pontuacao)
    c2.metric("Rodadas", jogo.estado.rodadas_jogadas)
    if jogo.estado.rodadas_jogadas:
        c3.metric("Acertos", f"{jogo.estado.acertos}/{jogo.estado.rodadas_jogadas}")
    else:
        c3.metric("Acertos", "—")


def coletar_indicios() -> list:
    """Renderiza os 4 grupos de perguntas e devolve a lista de itens marcados.

    A key de cada checkbox inclui o número da rodada atual (rodadas_jogadas).
    Assim, ao trocar de rodada, as keys mudam e o Streamlit cria checkboxes
    novos e desmarcados — sem reaproveitar o estado da rodada anterior (era o
    que causava perguntas/respostas "grudadas" entre rodadas).
    """
    rodada_id = st.session_state.jogo.estado.rodadas_jogadas
    st.write("**Por que você desconfiou?** (opcional)")
    marcados = []
    for pergunta, opcoes in INDICIOS.items():
        with st.expander(pergunta):
            for opcao in opcoes:
                if st.checkbox(opcao, key=f"chk_{rodada_id}_{opcao}"):
                    marcados.append(opcao)
    return marcados

# ---------------------------------------------------------------------------
# Telas (fases) do jogo
# ---------------------------------------------------------------------------
def tela_jogando(jogo: Jogo) -> None:
    rodada = st.session_state.rodada
    m = rodada.manchete

    st.subheader("Notícia da rodada")
    # Card com título (negrito), fonte (em itálico/menor) e corpo.
    st.markdown(
        f'<div class="bloco-noticia">'
        f'<div class="noticia-titulo">{m.titulo}</div>'
        f'<div class="noticia-fonte">Fonte: {m.fonte_exibida}</div>'
        f'<div class="noticia-corpo">{m.corpo}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Tópico: {m.topico} · dificuldade {m.dificuldade}/5")

    voto = st.radio("O que você acha?", ["Real", "Fake"],
                    horizontal=True, index=None)

    indicios = coletar_indicios() if voto == "Fake" else []

    if voto and st.button("Enviar avaliação", type="primary"):
        with st.spinner("Checador e Juiz analisando..."):
            jogo.finalizar_rodada(rodada, voto.lower(), indicios)
        st.session_state.fase = "feedback"
        st.rerun()


def tela_feedback(jogo: Jogo) -> None:
    rodada = st.session_state.rodada

    st.subheader("Resultado")
    if rodada.acertou:
        st.success(f"Você acertou!  +{rodada.pontos_ganhos} pontos")
    else:
        st.error(f"Não foi dessa vez. A notícia era **{rodada.manchete.veracidade}**.")

    st.markdown("**Feedback do Juiz**")
    st.write(rodada.feedback_juiz)

    # Detalhes técnicos do Checador, recolhidos por padrão.
    with st.expander("Ver análise do Checador"):
        c = rodada.saida_checador
        st.write(f"Classe prevista: **{c['classe']}** "
                 f"({c['prob_fake']:.0%} de chance de fake) — modo `{c['modo']}`")
        st.write("Indicadores de superfície:")
        st.json(c["features_superficie"])

    if st.button("Próxima rodada", type="primary"):
        st.session_state.rodada = jogo.nova_rodada()
        st.session_state.fase = "jogando"
        st.rerun()


def tela_inicio(jogo: Jogo) -> None:
    st.write("Leia cada notícia e decida se é **real** ou **fake**. "
             "Se achar que é fake, marque o que te deixou desconfiado.")
    if st.button("Começar a jogar", type="primary"):
        st.session_state.rodada = jogo.nova_rodada()
        st.session_state.fase = "jogando"
        st.rerun()


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Caça à Fake News", page_icon="📰",
                       layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)

    iniciar_estado()
    jogo = st.session_state.jogo

    st.title("📰 Caça à Fake News")
    st.caption("Jogo educativo de detecção de desinformação")

    # Aviso discreto quando rodando em modo demo (sem Gemini / sem modelo).
    if not config.TEM_API or not config.TEM_MODELO:
        st.info("Rodando em **modo demo** (sem Gemini e/ou sem Checador treinado). "
                "O jogo funciona normalmente com exemplos e heurística.",
                icon="ℹ️")

    barra_status(jogo)
    st.divider()

    # Despacha para a tela correta conforme a fase atual.
    fase = st.session_state.fase
    if fase == "inicio":
        tela_inicio(jogo)
    elif fase == "jogando":
        tela_jogando(jogo)
    elif fase == "feedback":
        tela_feedback(jogo)


if __name__ == "__main__":
    main()
