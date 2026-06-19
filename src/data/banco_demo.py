"""
Banco de notícias de exemplo para o MODO DEMO do Fofoqueiro.

Quando não há chave do Gemini, o Fofoqueiro sorteia uma notícia daqui em vez
de gerar via LLM. Todos os textos são SINTÉTICOS e escritos para fins
educativos:

  - As "fake" exibem indícios reais de desinformação (sensacionalismo, fonte
    vaga ou inventada, número solto, apelo à urgência).
  - As "real" usam tom jornalístico sóbrio e fonte plausível/verificável.
  - Nenhuma cita pessoas reais nem traz desinformação perigosa (saúde, etc.).

Cada item tem:
  - titulo      : a manchete (chamada da notícia)
  - fonte       : quem publicou. Em fakes pode ser vaga ("um amigo"), inventada
                  ("Portal Verdade Oculta") ou ausente (None). Isso é uma PISTA.
  - corpo       : o texto da notícia
  - veracidade  : "real" ou "fake"  -> GABARITO
  - dificuldade : 1 (pistas óbvias) a 5 (sutil, sem marcadores de superfície)
  - topico      : assunto, para exibição
"""

BANCO_NOTICIAS = [
    # ---------------- FAKE, dificuldade baixa (pistas óbvias) ----------------
    {
        "titulo": "ÁGUA COM LIMÃO EM JEJUM ELIMINA 100% DAS GRIPES, DIZEM CIENTISTAS!!!",
        "fonte": None,  # sem fonte: pista forte
        "corpo": (
            "URGENTE!!! A indústria farmacêutica NÃO QUER que você saiba disso! "
            "Basta tomar água com limão em jejum para nunca mais ter gripe. "
            "COMPARTILHE antes que APAGUEM!"
        ),
        "veracidade": "fake",
        "dificuldade": 1,
        "topico": "saúde",
    },
    {
        "titulo": "PREFEITURA VAI DAR CELULAR DE GRAÇA PARA TODOS NESTA SEMANA!",
        "fonte": "Um amigo que trabalha lá",  # fonte vaga/anedótica
        "corpo": (
            "BOMBA! A prefeitura vai DISTRIBUIR celulares de graça para TODOS os "
            "moradores. Corre que é só até sexta! Não perca essa chance!"
        ),
        "veracidade": "fake",
        "dificuldade": 1,
        "topico": "cidade",
    },
    # ---------------- FAKE, dificuldade média --------------------------------
    {
        "titulo": "Estudo aponta que dormir menos melhora as notas dos estudantes",
        "fonte": "Portal Saber Total",  # veículo desconhecido/inventado
        "corpo": (
            "Segundo a publicação, 9 em cada 10 estudantes que dormem menos passam "
            "de ano com notas melhores. A pesquisa foi divulgada em um grupo de "
            "mensagens e ainda não foi publicada em nenhuma revista científica."
        ),
        "veracidade": "fake",
        "dificuldade": 3,
        "topico": "educação",
    },
    {
        "titulo": "Nova lei obriga comércio a aceitar apenas dinheiro a partir do mês que vem",
        "fonte": None,
        "corpo": (
            "A informação circula em redes sociais e afirma que todos os "
            "comerciantes só poderão aceitar pagamento em dinheiro. Não há, porém, "
            "número de lei nem menção a publicação em diário oficial."
        ),
        "veracidade": "fake",
        "dificuldade": 3,
        "topico": "economia",
    },
    # ---------------- FAKE, dificuldade alta (sutil) -------------------------
    {
        "titulo": "Cidade registra queda de 40% em alagamentos após novos bueiros",
        "fonte": "Assessoria de imprensa municipal",
        "corpo": (
            "Levantamento aponta redução de 40% no número de alagamentos após a "
            "instalação de novos bueiros. O dado, no entanto, compara um ano de "
            "seca com um ano chuvoso, o que distorce a comparação."
        ),
        "veracidade": "fake",
        "dificuldade": 5,
        "topico": "meio ambiente",
    },
    # ---------------- REAL, dificuldade variada ------------------------------
    {
        "titulo": "Calendário escolar do próximo ano começará em fevereiro",
        "fonte": "Secretaria Municipal de Educação",
        "corpo": (
            "A Secretaria de Educação informou que o próximo ano letivo começará "
            "em fevereiro. As datas foram publicadas no diário oficial do município "
            "e estão disponíveis no site da secretaria."
        ),
        "veracidade": "real",
        "dificuldade": 2,
        "topico": "educação",
    },
    {
        "titulo": "Pesquisa monitora qualidade do ar e aponta variação na seca",
        "fonte": "Revista científica revisada por pares",
        "corpo": (
            "Pesquisadores de uma universidade pública publicaram um artigo sobre "
            "monitoramento da qualidade do ar na região. O estudo indica variação "
            "maior nos meses mais secos do ano."
        ),
        "veracidade": "real",
        "dificuldade": 4,
        "topico": "ciência",
    },
    {
        "titulo": "Instituto emite alerta de chuvas intensas para o fim de semana",
        "fonte": "Instituto Nacional de Meteorologia",
        "corpo": (
            "O instituto de meteorologia emitiu um alerta de chuvas intensas para "
            "parte do estado neste fim de semana. A recomendação é evitar áreas "
            "sujeitas a alagamento. O aviso traz data, validade e região."
        ),
        "veracidade": "real",
        "dificuldade": 3,
        "topico": "meio ambiente",
    },
    {
        "titulo": "Prefeitura abre inscrições para capacitação profissional gratuita",
        "fonte": "Portal oficial da prefeitura",
        "corpo": (
            "A prefeitura abriu inscrições para um programa de capacitação "
            "profissional gratuito. As vagas, os pré-requisitos e o prazo final "
            "constam no edital publicado no portal oficial da cidade."
        ),
        "veracidade": "real",
        "dificuldade": 2,
        "topico": "cidade",
    },
]
