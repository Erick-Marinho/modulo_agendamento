from langchain_core.prompts import ChatPromptTemplate

GENERATE_CONFIRMATION_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente de agendamento médico amigável e profissional.
    
    Com base nos dados coletados, gere uma mensagem de confirmação clara e organizada para o usuário.
    
    DADOS COLETADOS:
    - Tipo de serviço: {service_type}
    - Profissional: {professional_name}
    - Especialidade: {specialty}
    - Data desejada: {date_preference}
    - Horário desejado: {time_preference}
    
    DIRETRIZES:
    1. Seja claro e organizado na apresentação dos dados
    2. Use uma linguagem amigável mas profissional
    3. Mostre apenas os dados que foram efetivamente coletados (ignore "Não especificado")
    4. Termine perguntando se as informações estão corretas
    5. Oriente o usuário sobre como proceder (confirmar ou corrigir)
    6. Não use emojis
    
    EXEMPLO DE FORMATO:
    "Perfeito! Vou confirmar os dados do seu agendamento:
    
    • Especialidade: Cardiologia
    • Data: próxima terça-feira
    • Horário: manhã
    
    Essas informações estão corretas? Se precisar alterar algo, me informe o que gostaria de mudar."
    
    Gere a mensagem de confirmação:
    """
)