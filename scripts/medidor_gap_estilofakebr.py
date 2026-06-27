"""
5º experimento (controlado): notícias sintéticas que IMITAM o formato do Fake.br.

Pergunta isolada: o Checador falha com notícia de LLM por ela ser SINTÉTICA,
ou por ela ter FORMATO diferente do Fake.br (curta, outro estilo)?

Para responder, este script pede ao Gemini notícias LONGAS, em tom jornalístico
de portal, imitando o estilo do corpus Fake.br (2016-2018). Mantém o formato
fixo e varia só a origem (sintética). Compara o acerto do Checador aqui com o
acerto nas notícias sintéticas "normais" (script medir_gap_sintetico).

  - Se o Checador ACERTAR aqui (mas errava nas curtas) -> a causa era o FORMATO.
  - Se CONTINUAR errando -> a causa é a origem sintética em si.

NOTA DE HONESTIDADE (reportar no relatório): este é um teste ADVERSARIAL —
as notícias são deliberadamente construídas para imitar a distribuição de
treino. Não representam notícias sintéticas "naturais", e sim uma sonda para
isolar o efeito do formato.

Uso:
    python -m scripts.medir_gap_formato_fakebr --n 10
    python -m scripts.medir_gap_formato_fakebr --relatorio
    python -m scripts.medir_gap_formato_fakebr --zerar

Pré-requisitos: GOOGLE_API_KEY no .env e Checador treinado.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src import config
from src.agents.checador import Checador
from src.agents.gemini_utils import chamar_com_retry

ARQUIVO = Path("data/resultados_gap_formato.json")
TOPICOS = ["política", "economia", "saúde", "segurança pública",
           "educação", "meio ambiente", "tecnologia", "esportes"]

# Prompt que imita o formato/estilo do Fake.br: notícia LONGA, jornalística.
PROMPT_SISTEMA_FAKEBR = """Você gera notícias em português no estilo de grandes \
portais jornalísticos brasileiros do período 2016-2018 (como os do corpus \
Fake.br). Características OBRIGATÓRIAS do texto:
- Longo: entre 250 e 400 palavras (vários parágrafos).
- Tom jornalístico formal e sóbrio, terceira pessoa.
- Estrutura de notícia: lide no início, depois desenvolvimento com contexto,
  declarações e detalhes.
- Vocabulário e estilo de jornal impresso/portal da época.
- SEM emojis, SEM caixa-alta de alarme, SEM apelo para compartilhar.

Quando pedirem REAL: notícia plausível e factual sobre o tópico.
Quando pedirem FAKE: desinformação no mesmo tom sóbrio (sem marcadores óbvios),
respeitando limites: não citar pessoas reais por nome, não dar desinformação
perigosa de saúde, não incitar ódio.

Responda APENAS com o texto da notícia (sem título separado, sem comentários)."""


def carregar():
    return json.loads(ARQUIVO.read_text(encoding="utf-8")) if ARQUIVO.exists() else []


def salvar(dados):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def aviso_espera(seg, tent):
    print(f"      (API ocupada — aguardando {seg:.0f}s, tentativa {tent})")


def gerar_noticia_fakebr(cliente, topico, veracidade):
    """Gera uma notícia longa estilo Fake.br via Gemini (nova SDK)."""
    from google.genai import types
    prompt = f"Tópico: {topico}\nVeracidade: {veracidade.upper()}"
    resp = cliente.models.generate_content(
        model=config.MODELO_GEMINI,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=PROMPT_SISTEMA_FAKEBR),
    )
    return resp.text.strip()


def coletar(n):
    if not config.TEM_API:
        sys.exit("ERRO: sem GOOGLE_API_KEY no .env.")
    if not config.TEM_MODELO:
        sys.exit("ERRO: Checador não treinado.")

    from google import genai
    cliente = genai.Client(api_key=config.GOOGLE_API_KEY)
    checador = Checador()
    resultados = carregar()

    metade = n // 2
    pedidos = ["fake"] * (n - metade)
    print(f"Gerando {n} notícias estilo Fake.br "
          f"({pedidos.count('real')} reais, {pedidos.count('fake')} fakes). "
          f"Acumulado: {len(resultados)}.\n")

    for i, veracidade in enumerate(pedidos):
        topico = TOPICOS[i % len(TOPICOS)]
        try:
            texto = chamar_com_retry(gerar_noticia_fakebr, cliente, topico,
                                     veracidade, on_espera=aviso_espera)
            saida = checador.prever(texto)
        except Exception as e:
            print(f"  [{i+1}/{n}] FALHOU ({type(e).__name__}); pulando.\n")
            continue

        acertou = (saida["classe"] == veracidade)
        n_palavras = len(texto.split())
        resultados.append({
            "gabarito": veracidade,
            "previsto": saida["classe"],
            "prob_fake": saida["prob_fake"],
            "acertou": acertou,
            "n_palavras": n_palavras,
            "inicio": texto[:80],
        })
        salvar(resultados)
        marca = "OK " if acertou else "ERRO"
        print(f"  [{i+1}/{n}] pedido={veracidade.upper():4} -> {saida['classe'].upper():4} "
              f"[{marca}] prob_fake={saida['prob_fake']:.0%} ({n_palavras} palavras)")
        time.sleep(1.5)

    print(f"\nConcluído. Acumulado: {len(resultados)}.")
    relatorio()


def relatorio():
    res = carregar()
    if not res:
        sys.exit("Nada coletado ainda.")
    total = len(res)
    ac = sum(1 for r in res if r["acertou"])
    print("\n" + "=" * 54)
    print("CHECADOR EM NOTÍCIAS SINTÉTICAS NO FORMATO FAKE.BR")
    print("=" * 54)
    print(f"Total: {total} | Acurácia geral: {ac/total:.1%} ({ac}/{total})")
    media_pal = sum(r["n_palavras"] for r in res) / total
    print(f"Tamanho médio: {media_pal:.0f} palavras (Fake.br é longo)\n")
    for classe in ["real", "fake"]:
        sub = [r for r in res if r["gabarito"] == classe]
        if sub:
            a = sum(1 for r in sub if r["acertou"])
            pm = sum(r["prob_fake"] for r in sub) / len(sub)
            print(f"  {classe:5}: {a/len(sub):5.1%} ({a}/{len(sub)}) | prob_fake média {pm:.0%}")
    print("\nCompare com medir_gap_sintetico (notícias curtas):")
    print("  Se o acerto da classe REAL subiu aqui -> a causa era o FORMATO.")
    print("  Se continuou ~0% -> a causa é a origem sintética em si.")
    print("=" * 54)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--relatorio", action="store_true")
    p.add_argument("--zerar", action="store_true")
    a = p.parse_args()
    if a.zerar:
        if ARQUIVO.exists():
            ARQUIVO.unlink()
        print("Acumulado apagado.")
    elif a.relatorio:
        relatorio()
    else:
        coletar(a.n)


if __name__ == "__main__":
    main()