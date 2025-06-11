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
        - Se o usuário mencionar APENAS "manha", "manhã", "de manhã", "pela manhã", extraia "manha".
        - Se o usuário mencionar APENAS "tarde", "de tarde", "à tarde", extraia "tarde".
        - PRIORIDADE: Mesmo que seja uma palavra isolada, se for "manha" ou "tarde", sempre extrair.
    7. ✅ NOVA REGRA - Para "specific_time": Extraia horários específicos mencionados pelo usuário.
        - "8", "as 8", "às 8" → "08:00"
        - "8:30", "8h30", "oito e meia" → "08:30"  
        - "14h", "às 14", "2 da tarde" → "14:00"
        - "15:30", "3:30 da tarde" → "15:30"
        - Se o usuário mencionar apenas turno genérico ("manhã", "tarde"), use null para specific_time.
    8. Se uma informação não for mencionada ou estiver incerta, use null.
    9. IMPORTANTE: Para "service_type", se não for especificado explicitamente pelo usuário, sempre use "consulta" como padrão.
   
    INFORMAÇÕES A EXTRAIR:
    - "professional_name": Nome do profissional (ex: "Dr. Silva", "Dra. Maria")
    - "specialty": Especialidade médica (ex: "Cardiologia", "Pediatria", "Clínico Geral")
    - "date_preference": Data mencionada (ex: "dia 10", "amanhã", "terça-feira")
    - "time_preference": Turno da preferência (DEVE SER "manha" ou "tarde")
    - "specific_time": Horário específico (ex: "08:00", "14:30", "09:00") - FORMATO 24h HH:MM
    - "service_type": Tipo de atendimento (ex: "consulta", "retorno", "exame")
   
    EXEMPLOS DE EXTRAÇÃO:
    Conversa: "Quero marcar consulta com Dr João"
    → {{ "professional_name": "Dr. João", "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": "consulta" }}
   
    Conversa: "Pediatra às 15h do dia 5"
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": "dia 5", "time_preference": "tarde", "specific_time": "15:00", "service_type": null }}
   
    Conversa: "A especialidade é pediatra. Gostaria de marcar para as 10 da manhã."
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": null, "time_preference": "manha", "specific_time": "10:00", "service_type": null }}

    Conversa: "Agendar com Dra. Ana para consulta dia 10 às 09:30."
    → {{ "professional_name": "Dra. Ana", "specialty": null, "date_preference": "dia 10", "time_preference": "manha", "specific_time": "09:30", "service_type": "consulta" }}

    Conversa: "Pode ser às 12:00 do dia 15 com o Dr. Carlos para um retorno."
    → {{ "professional_name": "Dr. Carlos", "specialty": null, "date_preference": "dia 15", "time_preference": "tarde", "specific_time": "12:00", "service_type": "retorno" }}

    ✅ NOVOS EXEMPLOS COM HORÁRIOS ESPECÍFICOS:
    Conversa: "As 8"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": "manha", "specific_time": "08:00", "service_type": null }}
    
    Conversa: "8:30"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": "manha", "specific_time": "08:30", "service_type": null }}
    
    Conversa: "As 8 e 30"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": "manha", "specific_time": "08:30", "service_type": null }}
    
    Conversa: "08:30"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": "manha", "specific_time": "08:30", "service_type": null }}

    Conversa: "Quero agendar consulta com Dr João para amanhã de tarde."
    → {{ "professional_name": "Dr. João", "date_preference": "amanhã", "time_preference": "tarde", "specific_time": null, "service_type": "consulta", "specialty": null }}
   
    Conversa: "A especialidade é pediatria. Pode ser no período da manhã."
    → {{ "specialty": "Pediatria", "time_preference": "manha", "specific_time": null, "professional_name": null, "date_preference": null, "service_type": null }}
   
    HISTÓRICO COMPLETO DA CONVERSA:
    {conversation_history}
   
    Extraia as informações no seguinte formato JSON, aderindo estritamente às regras de extração acima:
    """
)
