"""
Utilitários para chamadas ao Gemini com tolerância a limite de quota (429).

O plano gratuito do Gemini limita as requisições por minuto. Quando esse limite
é atingido, a API levanta um erro 429 (ResourceExhausted) que normalmente já
informa quantos segundos esperar antes de tentar de novo.

A função chamar_com_retry() envolve uma chamada ao modelo e, em caso de 429,
espera e tenta novamente — em vez de quebrar ou cair para conteúdo de banco.
Assim, toda notícia/feedback é sempre gerado de fato pelo Gemini.

Um callback opcional (on_espera) é chamado antes de cada espera, permitindo que
a interface mostre uma mensagem como "aguardando o limite da API...".
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


def _eh_erro_de_quota(erro: Exception) -> bool:
    """Reconhece o erro 429 sem precisar importar a classe específica."""
    nome = type(erro).__name__
    return nome == "ResourceExhausted" or "429" in str(erro) or "quota" in str(erro).lower()


def chamar_com_retry(
    funcao: Callable,
    *args,
    max_tentativas: int = 4,
    on_espera: Optional[Callable[[float, int], None]] = None,
    **kwargs,
):
    """
    Executa `funcao(*args, **kwargs)`, tratando erro de quota com espera + retry.

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
            if not _eh_erro_de_quota(e):
                raise  # erro diferente de quota: propaga normalmente
            ultimo_erro = e
            if tentativa == max_tentativas:
                break
            espera = _segundos_de_espera(e)
            if on_espera:
                on_espera(espera, tentativa)
            time.sleep(espera)
    raise ultimo_erro