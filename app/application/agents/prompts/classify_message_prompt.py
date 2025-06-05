from langchain_core.prompts import ChatPromptTemplate

CLASSIFY_MESSAGE_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente especializado em classificar mensagens de usuários de uma clínica médica.

    Analise a mensagem do usuário e classifique em UMA das categorias abaixo:

    CATEGORIAS:
    - "scheduling": Qualquer solicitação de agendamento, consulta, ou informação sobre horários/profissionais para marcar um agendamento.
    - "scheduling_info": Respostas do usuário fornecendo informações solicitadas para agendamento (nome, data, especialidade, etc.).
    - "greeting": Cumprimentos iniciais como "oi", "olá", "bom dia", "boa tarde".
    - "farewell": Despedidas como "tchau", "obrigado", "até logo", "encerrar".
    - "api_query": Perguntas diretas sobre listagem de especialidades da clínica ou busca por profissionais de uma especialidade específica, que podem ser respondidas por uma busca em um sistema externo.
    - "other": Perguntas gerais sobre a clínica, endereço, funcionamento que NÃO sejam sobre listagem de especialidades ou profissionais.
    - "unclear": Mensagens confusas ou incompreensíveis.

    DIRETRIZES:
    1. Se o usuário está claramente iniciando um agendamento: "scheduling"
    2. Se está respondendo a uma pergunta sobre agendamento: "scheduling_info"  
    3. Se está pedindo para listar especialidades ou profissionais: "api_query"
    4. Seja específico - não confunda saudação com início de agendamento.
    5. Na dúvida entre "scheduling" e "scheduling_info", escolha "scheduling".
    6. Se a pergunta é sobre "quais especialidades tem?" ou "liste os médicos de X especialidade", use "api_query".

    EXEMPLOS:
    "Quero marcar uma consulta" → scheduling
    "Preciso agendar com cardiologista" → scheduling
    "Dr. Silva" (resposta a pergunta sobre profissional) → scheduling_info
    "Amanhã às 14h" (resposta sobre horário) → scheduling_info
    "Pediatria" (resposta sobre especialidade) → scheduling_info
    "Quais especialidades vocês atendem?" → api_query
    "Tem cardiologista?" → api_query
    "Quais médicos são da área de pediatria?" → api_query
    "Gostaria de saber os profissionais de cardiologia" → api_query
    "Olá, bom dia!" → greeting
    "Tchau, obrigado!" → farewell
    "Qual o endereço da clínica?" → other
    "asdfghjkl" → unclear

    Mensagem do usuário: {user_query}

    Responda APENAS com o nome da categoria (sem aspas, sem explicação):
    """
)