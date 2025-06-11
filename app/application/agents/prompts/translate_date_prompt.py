# app/application/agents/prompts/translate_date_prompt.py
from langchain_core.prompts import ChatPromptTemplate

TRANSLATE_DATE_PROMPT = ChatPromptTemplate.from_template(
    """
    Sua única tarefa é converter uma frase em linguagem natural para uma data no formato YYYY-MM-DD.

    **Contexto:**
    - A data de hoje é: {current_date}
    - A frase do usuário a ser traduzida é: "{user_preference}"

    **Regras CRÍTICAS para "dia X":**
    1. Quando o usuário disser "dia X" (exemplo: "dia 20", "dia 23"), SEMPRE interprete como o dia X do MÊS ATUAL primeiro.
    2. Se estamos no meio do mês e o dia X ainda não chegou (ex: hoje é dia 11 e usuário pede "dia 20"), use o MÊS ATUAL.
    3. APENAS se o dia X já passou completamente no mês atual, considere o PRÓXIMO mês.
    4. Para determinar se já passou: se hoje é dia 11 e usuário pede "dia 8", então dia 8 já passou → próximo mês.
    5. Se o dia X não existe no mês atual (ex: dia 31 em fevereiro), use o próximo mês que tenha esse dia.

    **Exemplos ESPECÍFICOS (considerando hoje = 2025-06-11):**
    - "dia 20" → 2025-06-20 (junho, pois dia 20 ainda não chegou)
    - "dia 23" → 2025-06-23 (junho, pois dia 23 ainda não chegou)  
    - "dia 30" → 2025-06-30 (junho, pois dia 30 ainda não chegou)
    - "dia 8" → 2025-07-08 (julho, pois dia 8 de junho já passou)
    - "dia 31" → 2025-07-31 (julho, pois junho não tem dia 31)

    **Outras Regras:**
    6. Para outras frases ("amanhã", "próxima segunda"), interprete normalmente em relação à data atual.
    7. Retorne APENAS a data no formato YYYY-MM-DD.
    8. Não inclua explicações, aspas ou pontuação extra.
    9. Se não conseguir traduzir, retorne "invalid_date".

    **Exemplos de outras frases (hoje = 2025-06-11):**
    - "amanhã" → 2025-06-12
    - "depois de amanhã" → 2025-06-13
    - "próxima segunda-feira" → 2025-06-16

    **Sua Resposta (APENAS a data):**
    """
)
