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
    - "specialty_selection": Quando o usuário responde com apenas um nome de especialidade após ser mostrada uma lista de especialidades (ex: "Cardiologia", "Pediatria").
    - "other": Perguntas gerais sobre a clínica, endereço, funcionamento que NÃO sejam sobre listagem de especialidades ou profissionais.
    - "unclear": Mensagens confusas ou incompreensíveis.

    DIRETRIZES:
    1. Se o usuário está claramente iniciando um agendamento: "scheduling"
    2. Se está respondendo a uma pergunta sobre agendamento: "scheduling_info"  
    3. Se está pedindo para listar especialidades ou profissionais: "api_query"
    4. Se responde com apenas uma especialidade (como "Cardiologia") após ver uma lista: "specialty_selection"
    5. Seja específico - não confunda saudação com início de agendamento.
    6. Na dúvida entre "scheduling" e "scheduling_info", escolha "scheduling".
    7. Se a pergunta é sobre "quais especialidades tem?" ou "liste os médicos de X especialidade", use "api_query".

    EXEMPLOS:
    "Quero marcar uma consulta" → scheduling
    "Preciso agendar com cardiologista" → scheduling
    "Dr. Silva" (resposta a pergunta sobre profissional) → scheduling_info
    "Amanhã às 14h" (resposta sobre horário) → scheduling_info
    "amanha a tarde" (resposta sobre data e turno) → scheduling_info
    "Pediatria" (resposta sobre especialidade) → scheduling_info
    "Cardiologia" (após ver lista de especialidades) → specialty_selection
    "Ortopedia" (após ver lista de especialidades) → specialty_selection
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
