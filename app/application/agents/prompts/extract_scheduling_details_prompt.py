from langchain_core.prompts import ChatPromptTemplate

EXTRACT_SCHEDULING_DETAILS_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente especialista em extrair informações de agendamento médico de conversas.
   
    Analise TODO o histórico da conversa abaixo e extraia as informações de agendamento mais ATUALIZADAS e COMPLETAS.
   
    REGRAS IMPORTANTES:
    1. Se uma informação foi mencionada em qualquer parte da conversa, extraia ela.
    2. Se o usuário corrigir uma informação, use a correção mais recente.
    3. Seja FLEXÍVEL com variações de escrita (ex: "Dr Silvio" = "Dr. Silvio").
    4. Para especialidades, aceite variações (ex: "pediatra" = "Pediatria").
    5. Se uma informação não for mencionada EM NENHUM lugar, use null.
    6. Para "time_preference", o valor DEVE SER EXATAMENTE "manha" ou "tarde".
        - Se o usuário mencionar "manhã", "de manhã", "pela manhã", extraia "manha".
        - Se o usuário mencionar "tarde", "de tarde", "à tarde", extraia "tarde".
        - Mesmo que o usuário forneça um horário específico (ex: 10:00h), se a palavra "manhã" ou "tarde" estiver presente, priorize a palavra.
        - Se o turno não for claramente especificado como manhã ou tarde, use null.
    7. Se uma informação não for mencionada ou estiver incerta, use null.
   
    INFORMAÇÕES A EXTRAIR:
    - "professional_name": Nome do profissional (ex: "Dr. Silva", "Dra. Maria")
    - "specialty": Especialidade médica (ex: "Cardiologia", "Pediatria", "Clínico Geral")
    - "date_preference": Data mencionada (ex: "dia 10", "amanhã", "terça-feira")
    - "time_preference": Turno da preferência (DEVE SER "manha" ou "tarde").
    - "service_type": Tipo de atendimento (ex: "consulta", "retorno", "exame")
   
    EXEMPLOS DE EXTRAÇÃO:
    Conversa: "Quero marcar consulta com Dr João"
    → {{ "professional_name": "Dr. João", "specialty": null, "date_preference": null, "time_preference": null, "service_type": "consulta" }}
   
    Conversa: "Pediatra às 15h do dia 5"
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": "dia 5", "time_preference": "tarde", "service_type": null }}
   
    Conversa: "A especialidade é pediatra. Gostaria de marcar para as 10 da manhã."
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": null, "time_preference": "manha", "service_type": null }}

    Conversa: "Agendar com Dra. Ana para consulta dia 10 às 09:30."
    → {{ "professional_name": "Dra. Ana", "specialty": null, "date_preference": "dia 10", "time_preference": "manha", "service_type": "consulta" }}

    Conversa: "Pode ser às 12:00 do dia 15 com o Dr. Carlos para um retorno."
    → {{ "professional_name": "Dr. Carlos", "specialty": null, "date_preference": "dia 15", "time_preference": "tarde", "service_type": "retorno" }}

    Conversa: "Quero agendar consulta com Dr João para amanhã de tarde."
    → {{ "professional_name": "Dr. João", "date_preference": "amanhã", "time_preference": "tarde", "service_type": "consulta", "specialty": null }}
   
    Conversa: "A especialidade é pediatria. Pode ser no período da manhã."
    → {{ "specialty": "Pediatria", "time_preference": "manha", "professional_name": null, "date_preference": null, "service_type": null }}
   
    HISTÓRICO COMPLETO DA CONVERSA:
    {conversation_history}
   
    Extraia as informações no seguinte formato JSON, aderindo estritamente às regras de extração acima:
    """
)
