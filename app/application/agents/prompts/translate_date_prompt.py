# app/application/agents/prompts/translate_date_prompt.py
from langchain_core.prompts import ChatPromptTemplate

TRANSLATE_DATE_PROMPT = ChatPromptTemplate.from_template(
    """
    Sua única tarefa é converter uma frase em linguagem natural para uma data no formato YYYY-MM-DD.

    **Contexto:**
    - A data de hoje é: {current_date}
    - A frase do usuário a ser traduzida é: "{user_preference}"

    **Regras IMPORTANTES:**
    1. Quando o usuário disser apenas "dia X" (exemplo: "dia 13"), SEMPRE considere que é o dia X do MÊS ATUAL.
    2. Se o dia X já passou no mês atual, considere o dia X do PRÓXIMO MÊS.
    3. Interprete outras frases em relação à data de hoje.
    4. Retorne APENAS a data resultante no formato YYYY-MM-DD.
    5. Não inclua nenhuma outra palavra, explicação ou pontuação.
    6. Se a frase não puder ser traduzida para uma data válida, retorne "invalid_date".

    **Exemplos (considerando hoje = 2025-06-09, Segunda-feira):**
    - user_preference: "dia 13" -> Retorno: 2025-06-13
    - user_preference: "dia 8" -> Retorno: 2025-07-08 (pois dia 8 já passou)
    - user_preference: "amanhã" -> Retorno: 2025-06-10
    - user_preference: "próxima segunda-feira" -> Retorno: 2025-06-16
    - user_preference: "depois de amanhã" -> Retorno: 2025-06-11

    **Sua Resposta:**
    """
)
