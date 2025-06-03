from langchain_core.prompts import ChatPromptTemplate

EXTRACT_SCHEDULING_DETAILS_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente especialista em extrair informações de agendamento médico de conversas.
   
    Analise TODO o histórico da conversa abaixo e extraia as informações de agendamento mais ATUALIZADAS e COMPLETAS.
   
    REGRAS IMPORTANTES:
    1. Se uma informação foi mencionada em qualquer parte da conversa, extraia ela
    2. Se o usuário corrigir uma informação, use a correção mais recente
    3. Seja FLEXÍVEL com variações de escrita (ex: "Dr Silvio" = "Dr. Silvio")
    4. Para especialidades, aceite variações (ex: "pediatra" = "Pediatria")
    5. Se uma informação não for mencionada EM NENHUM lugar, use null
   
    INFORMAÇÕES A EXTRAIR:
    - "professional_name": Nome do profissional (ex: "Dr. Silva", "Dra. Maria")
    - "specialty": Especialidade médica (ex: "Cardiologia", "Pediatria", "Clínico Geral")
    - "date_preference": Data mencionada (ex: "dia 10", "amanhã", "terça-feira")
    - "time_preference": Horário mencionado (ex: "15:00", "3 da tarde", "manhã")
    - "service_type": Tipo de atendimento (ex: "consulta", "retorno", "exame")
   
    EXEMPLOS DE EXTRAÇÃO:
    Conversa: "Quero marcar consulta com Dr João"
    → professional_name: "Dr. João", service_type: "consulta"
   
    Conversa: "Pediatra às 15h do dia 5"
    → specialty: "Pediatria", time_preference: "15h", date_preference: "dia 5"
   
    Conversa: "A especialidade é pediatra"
    → specialty: "Pediatria"
   
    HISTÓRICO COMPLETO DA CONVERSA:
    {conversation_history}
   
    Extraia as informações em formato JSON:
    """
)