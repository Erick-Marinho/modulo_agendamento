from langchain_core.prompts import ChatPromptTemplate

ANALYZE_USER_INTENT_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um especialista em análise de intenções para sistema de agendamento médico.
    
    Analise o histórico completo da conversa e determine a intenção EXATA do usuário.
    
    HISTÓRICO DA CONVERSA:
    {conversation_history}
    
    DADOS EXISTENTES DO AGENDAMENTO:
    {existing_scheduling_details}
    
    MENSAGEM ATUAL DO USUÁRIO: 
    "{current_message}"
    
    DETERMINE A INTENÇÃO DO USUÁRIO:
    
    1. **CREATE** - Usuário quer criar um NOVO agendamento do zero
       - Exemplos: "Quero marcar consulta", "Agendar com Dr. Silva", "Preciso de uma consulta"
    
    2. **UPDATE** - Usuário quer ALTERAR/REMARCAR/CORRIGIR dados de agendamento existente
       - Exemplos: "Mudar o horário", "Trocar médico", "Não, quero outro dia", "Corrigir especialidade", "Quero alterar minha consulta", "Quero mudar minha consulta
    

    
    REGRAS IMPORTANTES:
    - Se não há dados existentes e usuário fala de agendamento = CREATE
    - Se há dados existentes e usuário quer mudar alguma informação de agendamento = UPDATE  
    - Na dúvida entre CREATE e UPDATE, prefira UPDATE se há dados existentes
    
    RESPONDA APENAS STRING:
    "CREATE|UPDATE|UNCLEAR"
    
    IMPORTANTE:
    - Se a intenção não está clara, responda com "UNCLEAR"

    """
)