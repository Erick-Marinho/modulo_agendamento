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

    ⚠️ **REGRA CRÍTICA**: Qualquer pergunta que contenha as palavras "quais", "que", "qual", "tem", "lista", "mostrar", "ver" seguida de "especialidades", "profissionais", "médicos", "doutor", "doutora" DEVE ser classificada como "api_query".

    DIRETRIZES DE PRIORIDADE:
    1. **PRIORIDADE MÁXIMA**: Perguntas sobre listar/mostrar especialidades ou profissionais → "api_query"
    2. Se o usuário está claramente iniciando um agendamento → "scheduling"
    3. Se está respondendo a uma pergunta sobre agendamento → "scheduling_info"
    4. Se responde com apenas uma especialidade após ver uma lista → "specialty_selection"
    5. Cumprimentos → "greeting" 
    6. Despedidas → "farewell"
    7. Outras perguntas sobre a clínica → "other"
    8. Mensagens confusas → "unclear"

    🎯 **CASOS OBRIGATÓRIOS PARA api_query:**
    - "quais especialidades" → api_query
    - "que especialidades" → api_query  
    - "quais as especialidades" → api_query
    - "quais são os profissionais" → api_query
    - "que profissionais" → api_query
    - "quais profissionais" → api_query
    - "quais médicos" → api_query
    - "que médicos" → api_query
    - "tem cardiologista" → api_query
    - "tem especialista" → api_query
    - "lista de especialidades" → api_query
    - "mostrar especialidades" → api_query
    - "ver especialidades" → api_query
    - "mostrar profissionais" → api_query
    - "ver profissionais" → api_query
    
    EXEMPLOS CLAROS:
    "Quero marcar uma consulta" → scheduling
    "Preciso agendar com cardiologista" → scheduling
    "quais são os profissionais?" → api_query ⚠️
    "que especialidades vocês tem?" → api_query ⚠️
    "Dr. Silva" (como resposta) → scheduling_info
    "Amanhã às 14h" (como resposta) → scheduling_info
    "Cardiologia" (após ver lista) → specialty_selection
    "Olá!" → greeting
    "Qual o endereço?" → other

    Mensagem do usuário: {user_query}

    ⚠️ **CONTEXTO CRÍTICO**: Se o usuário responder apenas "manha", "manhã", "tarde" em resposta a uma pergunta sobre turno de preferência, classifique como "scheduling_info".
    
    EXEMPLOS CONTEXTUAIS:
    "manha" (em resposta a pergunta sobre turno) → scheduling_info
    "tarde" (em resposta a pergunta sobre turno) → scheduling_info
    "08:00" (como resposta de horário) → scheduling_info

    Responda APENAS com o nome da categoria (sem aspas, sem explicação):
    """
)
