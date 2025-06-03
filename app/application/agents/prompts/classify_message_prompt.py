from langchain_core.prompts import ChatPromptTemplate

CLASSIFY_MESSAGE_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Classifique a seguinte mensagem do usuário em UMA das categorias abaixo:
 
    CATEGORIAS:
    - "scheduling": Qualquer coisa relacionada a agendar, marcar consulta, informar dados de agendamento, responder perguntas sobre agendamento
    - "greeting": Cumprimentos, saudações iniciais como "oi", "olá", "bom dia"  
    - "farewell": Despedidas como "tchau", "obrigado", "até logo"
    - "fallback_node": Apenas para mensagens completamente incompreensíveis ou não relacionadas
 
    IMPORTANTE:
    - Respostas a perguntas sobre agendamento são sempre "scheduling"
    - Informações sobre especialidade, médico, data, horário = "scheduling"
    - Seja INCLUSIVO - na dúvida, escolha "scheduling"
 
    EXEMPLOS:
    "Quero marcar consulta" → scheduling
    "Dr. Silva às 15h" → scheduling  
    "A especialidade é pediatria" → scheduling
    "Pediatra" → scheduling
    "Dia 10 às 15:00" → scheduling
    "Olá" → greeting
    "Tchau" → farewell
    "asdfghjkl" → fallback_node
 
    Mensagem do usuário: {user_query}
   
    Responda APENAS com o nome da categoria (sem aspas, sem explicação):
    """
)
