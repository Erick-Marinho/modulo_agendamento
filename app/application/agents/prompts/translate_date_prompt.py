# app/application/agents/prompts/translate_date_prompt.py
from langchain_core.prompts import ChatPromptTemplate

TRANSLATE_DATE_PROMPT = ChatPromptTemplate.from_template(
    """
    Sua única tarefa é converter uma frase em linguagem natural para uma data no formato YYYY-MM-DD.

    **Contexto:**
    - A data de hoje é: {current_date}
    - A frase do usuário a ser traduzida é: "{user_preference}"

    **Regras:**
    1.  Interprete a frase do usuário em relação à data de hoje.
    2.  Retorne APENAS a data resultante no formato YYYY-MM-DD.
    3.  Não inclua nenhuma outra palavra, explicação ou pontuação.
    4.  Se a frase não puder ser traduzida para uma data válida (ex: "no natal"), retorne a string "invalid_date".

    **Exemplos (considerando hoje = 2025-06-06, Sexta-feira):**
    - user_preference: "amanhã" -> Retorno: 2025-06-07
    - user_preference: "próxima segunda-feira" -> Retorno: 2025-06-09
    - user_preference: "dia 10" -> Retorno: 2025-06-10
    - user_preference: "depois de amanhã" -> Retorno: 2025-06-08
    - user_preference: "sexta que vem" -> Retorno: 2025-06-13

    **Sua Resposta:**
    """
)
