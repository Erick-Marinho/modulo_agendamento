from langchain_core.prompts import ChatPromptTemplate

SCHEDULING_VALIDATION_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Analise a seguinte resposta do usuário à pergunta de confirmação de agendamento:

    Mensagem do usuário: {user_query}

    Sua tarefa é identificar a intenção do usuário e, se houver, extrair quaisquer atributos de agendamento que ele deseja alterar, junto com os novos valores mencionados.

    **IMPORTANTE: Você DEVE retornar APENAS um objeto JSON válido, sem nenhum texto adicional antes ou depois.**

    Estrutura do JSON de resposta:
    {{
        "intent": "TIPO_INTENCAO",
        "change_details": {{}}
    }}

    Categorize a intenção do usuário da seguinte forma:

    CONFIRMED_SCHEDULING_DATA
    ALTER_SCHEDULING_DATA
    UNCLEAR

    1. **CONFIRMED_SCHEDULING_DATA**: O usuário está satisfeito com os dados e não quer alterações.
       Exemplo: {{"intent": "CONFIRMED_SCHEDULING_DATA", "change_details": {{}}}}

    2. **ALTER_SCHEDULING_DATA**: O usuário quer fazer alterações nos dados do agendamento.
       Exemplo: {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"date_preference": "15/03/2024", "time_preference": "14:00"}}}}

    3. **UNCLEAR**: A resposta é ambígua, irrelevante ou não permite determinar uma intenção clara de confirmação ou alteração.
       {{"intent": "UNCLEAR", "change_details": {{}}}}

    **Atributos de agendamento esperados para extração (usar estas chaves no JSON):**
    `professional_name`, `specialty`, `date_preference`, `time_preference`, `service_type`

    **Exemplos de Saída esperada (formato JSON):**

    Usuário: "Sim, está tudo correto."
        {{"intent": "CONFIRMED_SCHEDULING_DATA", "change_details": {{}}}}

    Usuário: "Quero mudar o horário para 15h e a especialidade para cardiologia."
        {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"time_preference": "15h", "specialty": "cardiologia"}}}}

    Usuário: "Sim, quero alterar as informações."
        {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"generic": true}}}}

    Usuário: "Quero alterar o dia."
        {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"date_preference": null}}}}

    Usuário: "Sim, mas e o estacionamento?"
        {{"intent": "UNCLEAR", "change_details": {{}}}}

    Usuário: "Quero mudar o especialista para a Dra. Fátima e a data para amanhã."
        {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"professional_name": "Dra. Fátima", "date_preference": "amanhã"}}}}

    Usuário: "Não."
        {{"intent": "ALTER_SCHEDULING_DATA", "change_details": {{"generic": true}}}}
    """
)