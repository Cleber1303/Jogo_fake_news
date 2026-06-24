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
import time

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
/* ===== Estilo "Jornal clássico" ===== */

/* Importa uma fonte serifada de jornal (Google Fonts). */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Lora:ital@0;1&display=swap');

/* Card da notícia: papel creme, borda fina, leve sombra. */
.bloco-noticia {
    background: #fbfaf6;
    color: #1a1a1a;
    border: 1px solid #e2ddd0;
    border-top: 3px solid #2e2a25;
    border-radius: 4px;
    padding: 22px 26px;
    margin: 8px 0 4px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
/* Título: serifado, grande, como manchete de jornal. */
.noticia-titulo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1.25;
    color: #1a1714;
    margin-bottom: 10px;
}
/* Fonte: itálico, menor, com linha separadora embaixo. */
.noticia-fonte {
    font-family: 'Lora', Georgia, serif;
    font-size: 0.85rem;
    font-style: italic;
    color: #6b6358;
    border-bottom: 1px solid #e2ddd0;
    padding-bottom: 10px;
    margin-bottom: 14px;
}
/* Corpo: serifado, leitura confortável. */
.noticia-corpo {
    font-family: 'Lora', Georgia, serif;
    font-size: 1.05rem;
    line-height: 1.6;
    color: #2c2825;
}

/* Título do jogo no topo, em fonte de jornal.
   Usa a cor de texto do tema do Streamlit (inherit), que já é clara no tema
   escuro e escura no tema claro — assim o título aparece nos dois modos. */
.titulo-jogo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: inherit;
    text-align: center;
    letter-spacing: 0.5px;
    border-bottom: 2px solid currentColor;
    border-top: 2px solid currentColor;
    padding: 6px 0;
    margin-bottom: 4px;
}
.subtitulo-jogo {
    font-family: 'Lora', Georgia, serif;
    font-style: italic;
    text-align: center;
    color: inherit;
    opacity: 0.7;
    font-size: 0.95rem;
    margin-bottom: 8px;
}

/* Botões do Streamlit (Enviar, Próxima, Começar): cantos retos de jornal.
   Não fixamos cor de texto/fundo aqui — são type="primary", então o Streamlit
   já cuida do contraste nos dois temas. Só ajustamos o formato. */
.stButton > button {
    border-radius: 4px;
    font-weight: 600;
}

/* Deixa o radio Real/Fake parecido com dois selos.
   O fundo é claro (#fbfaf6), então fixamos o texto escuro — senão, no tema
   escuro, o texto fica branco sobre fundo claro e some. O seletor cobre tanto
   o container do label quanto o texto interno do Streamlit. */
div[role="radiogroup"] label {
    border: 1px solid #cfc8ba;
    border-radius: 4px;
    padding: 6px 16px;
    margin-right: 8px;
    background: #fbfaf6;
    font-weight: 600;
}
div[role="radiogroup"] label,
div[role="radiogroup"] label p,
div[role="radiogroup"] label div {
    color: #2c2825 !important;
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
def criar_aviso_espera():
    """
    Cria um callback on_espera(segundos, tentativa) que mostra na tela um aviso
    enquanto o jogo aguarda o limite da API do Gemini liberar.
    """
    placeholder = st.empty()

    def on_espera(segundos: float, tentativa: int) -> None:
        for restante in range(int(segundos), 0, -1):
            placeholder.warning(
                f"⏳ Gerando com IA — o serviço está ocupado, tentando novamente "
                f"em {restante}s...",
                icon="⏳",
            )
            time.sleep(1)

    return placeholder, on_espera

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
        placeholder, on_espera = criar_aviso_espera()
        with st.spinner("Checador e Juiz analisando..."):
            jogo.finalizar_rodada(rodada, voto.lower(), indicios,
                                  on_espera=on_espera)
        placeholder.empty()
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

    # Detalhamento dos indícios (só aparece em fakes acertadas com marcações).
    if rodada.acertou and rodada.manchete.veracidade == "fake":
        if rodada.indicios_corretos or rodada.indicios_errados or rodada.indicios_perdidos:
            st.markdown("**Seus indícios**")
            for ind in rodada.indicios_corretos:
                st.markdown(f"✅ {ind}  ·  +3")
            for ind in rodada.indicios_errados:
                st.markdown(f"❌ {ind}  ·  −2 (não se aplica a esta notícia)")
            for ind in rodada.indicios_perdidos:
                st.markdown(f"➖ {ind}  ·  (estava presente, você não marcou)")

    # Detalhes técnicos do Checador, recolhidos por padrão.
    with st.expander("Ver análise do Checador"):
        c = rodada.saida_checador
        st.write(f"Classe prevista: **{c['classe']}** "
                 f"({c['prob_fake']:.0%} de chance de fake) — modo `{c['modo']}`")
        st.write("Indicadores de superfície:")
        st.json(c["features_superficie"])

    if st.button("Próxima rodada", type="primary"):
        placeholder, on_espera = criar_aviso_espera()
        with st.spinner("Fofoqueiro escrevendo a notícia..."):
            st.session_state.rodada = jogo.nova_rodada(on_espera=on_espera)
        placeholder.empty()
        st.session_state.fase = "jogando"
        st.rerun()


def tela_inicio(jogo: Jogo) -> None:
    st.write("Leia cada notícia e decida se é **real** ou **fake**. "
             "Se achar que é fake, marque o que te deixou desconfiado.")
    if st.button("Começar a jogar", type="primary"):
        placeholder, on_espera = criar_aviso_espera()
        with st.spinner("Fofoqueiro escrevendo a notícia..."):
            st.session_state.rodada = jogo.nova_rodada(on_espera=on_espera)
        placeholder.empty()
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

    st.markdown('<div class="titulo-jogo">Caça à Fake News</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="subtitulo-jogo">Jogo educativo de detecção de desinformação</div>',
                unsafe_allow_html=True)

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