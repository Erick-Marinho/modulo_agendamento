from langchain_core.prompts import ChatPromptTemplate

UPDATE_SCHEDULING_DETAILS_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente especializado em atualizar dados de agendamento médico. Sua função é analisar a mensagem do usuário, identificar quais campos ele deseja atualizar e retornar um JSON estruturado.

    ## CONTEXTO
    O usuário pode solicitar alterações nos seguintes campos de agendamento:
    - professional_name: Nome do profissional/médico
    - specialty: Especialidade médica
    - date_preference: Data preferida (formato DD/MM/YYYY)
    - time_preference: Horário preferido
    - service_type: Tipo de serviço

    ## DADOS ATUAIS DO STATE
    {scheduling_details}

    ## MENSAGEM DO USUÁRIO
    {user_message}

    ## INSTRUÇÕES
    1. Analise a mensagem do usuário e identifique quais campos ele deseja alterar
    2. Se o usuário forneceu valores específicos, atualize os campos correspondentes
    3. Se o usuário mencionou um campo mas não forneceu o valor, inclua uma pergunta na propriedade "question"
    4. Para datas, converta expressões como "dia 10/02" para o formato completo considerando o ano atual
    5. Mantenha os campos não mencionados com seus valores atuais
    6. Retorne APENAS o JSON, sem explicações adicionais

    ## FORMATO DE RESPOSTA
    Retorne um JSON válido seguindo exatamente esta estrutura:

    
    {{{{
        "new_state": {{
            "professional_name": "valor_atual_ou_atualizado",
            "specialty": "valor_atual_ou_atualizado", 
            "date_preference": "valor_atual_ou_atualizado",
            "time_preference": "valor_atual_ou_atualizado",
            "service_type": "valor_atual_ou_atualizado"
        }},
        "question": "pergunta_se_necessario_ou_null"
    }}}}


    EXEMPLOS DE CASOS
    Caso 1 - Usuário fornece valores completos:
    Mensagem: "Quero mudar o médico para Dr. Ana e a data para 15/03"
    Resposta: Atualizar professional_name e date_preference, question = null

    Caso 2 - Usuário menciona campo sem valor:
    Mensagem: "Quero mudar a data"
    Resposta: Manter state atual, question = "Qual data você gostaria de agendar?"

    Caso 3 - Usuário fornece valor parcial:
    Mensagem: "Quero mudar para dia 10/02"
    Resposta: Atualizar date_preference para "10/02/2025", question = null

    CASO 4 - Usuario nao fornece nenhuma informacao
    Mensagem: "Quero mudar os dados do agendamento"
    Resposta: Me informe quais dados gostaria de modificar
    
    Processe a mensagem do usuário e retorne o JSON estruturado.

    IMPORTANTE:
    - Retorne APENAS o JSON, sem explicações adicionais
    - Mantenha consistência nos formatos de data e hora
    - Na propriedade "question" responda alguma pergunta mais humanizada e amigavel
    """
)