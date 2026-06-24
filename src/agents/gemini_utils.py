"""
Utilitários para chamadas ao Gemini com tolerância a erros temporários.

A API do Gemini pode falhar temporariamente por:
  - 429 (quota): muitas requisições por minuto no plano gratuito.
  - 503 (UNAVAILABLE): modelo sobrecarregado por alta demanda.
  - 500 (INTERNAL): erro interno transitório.

Todos esses costumam se resolver sozinhos. A função chamar_com_retry() envolve
uma chamada ao modelo e, nesses casos, espera e tenta novamente — em vez de
quebrar. Assim, toda notícia/feedback é de fato gerado pelo Gemini.

Um callback opcional (on_espera) é chamado antes de cada espera, permitindo que
a interface mostre uma mensagem de "aguardando..." ao jogador.
"""

import re
import time
from typing import Callable, Optional


def _segundos_de_espera(erro: Exception, padrao: float = 6.0) -> float:
    """
    Extrai do texto do erro 429 quantos segundos esperar.

    A mensagem da API costuma conter algo como "retry in 5.4s" ou um campo
    "retry_delay { seconds: 5 }". Se não acharmos, usamos um padrão seguro.
    """
    texto = str(erro)
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", texto, re.IGNORECASE)
    if m:
        return float(m.group(1)) + 0.5  # margem de segurança
    m = re.search(r"seconds:\s*(\d+)", texto)
    if m:
        return float(m.group(1)) + 1.0
    return padrao


def _eh_erro_temporario(erro: Exception) -> bool:
    """Reconhece erros TEMPORÁRIOS que vale a pena tentar de novo (com espera).

    Cobre, nas duas SDKs:
      - 429 (quota): muitas requisições por minuto.
      - 503 (UNAVAILABLE): modelo sobrecarregado ("high demand").
      - 500 (INTERNAL): erro interno transitório do servidor.
    Todos esses costumam se resolver sozinhos ao tentar novamente. Erros
    diferentes (ex.: 401 autenticação, 404 modelo inexistente) NÃO entram aqui,
    pois repetir não adianta — eles são propagados.
    """
    nome = type(erro).__name__
    codigo = getattr(erro, "code", None)
    texto = str(erro).lower()
    return (
        nome == "ResourceExhausted"
        or codigo in (429, 500, 503)
        or "429" in texto
        or "quota" in texto
        or "503" in texto
        or "500" in texto
        or "unavailable" in texto
        or "high demand" in texto
        or "overloaded" in texto
    )


def chamar_com_retry(
    funcao: Callable,
    *args,
    max_tentativas: int = 5,
    on_espera: Optional[Callable[[float, int], None]] = None,
    **kwargs,
):
    """
    Executa `funcao(*args, **kwargs)`, tratando erros temporários (429/503/500)
    com espera + nova tentativa.

    Parâmetros:
        funcao        : a função que faz a chamada ao Gemini.
        max_tentativas: quantas vezes tentar antes de desistir.
        on_espera     : callback opcional on_espera(segundos, tentativa), chamado
                        antes de cada espera (para a UI exibir um aviso).

    Levanta o erro original se esgotar as tentativas.
    """
    ultimo_erro = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            return funcao(*args, **kwargs)
        except Exception as e:
            if not _eh_erro_temporario(e):
                raise  # erro não-temporário (ex.: 401): repetir não adianta
            ultimo_erro = e
            if tentativa == max_tentativas:
                break
            # Tempo de espera: usa o que a API sugerir (429) ou um backoff
            # crescente (503/500 não trazem "retry in", então esperamos cada
            # vez um pouco mais: ~4s, 8s, 12s, 16s).
            espera_sugerida = _segundos_de_espera(e, padrao=0)
            espera = espera_sugerida if espera_sugerida > 0 else 4.0 * tentativa
            if on_espera:
                on_espera(espera, tentativa)
            time.sleep(espera)
    raise ultimo_erro