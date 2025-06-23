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
        - "8 e 30", "8 e trinta", "oito e trinta", "as 8 e 30" → "08:30"
        - "9 e 15", "nove e quinze", "as 9 e 15" → "09:15"
        - "14h", "às 14", "2 da tarde" → "14:00"
        - "15:30", "3:30 da tarde" → "15:30"
        - Se o usuário mencionar apenas turno genérico ("manhã", "tarde"), use null para specific_time.
    8. ✅ NOVA REGRA CRÍTICA - Para "date_preference": SEMPRE aceite expressões de proximidade temporal.
        - "a mais próxima", "mais próxima", "a mais proxima", "mais proxima" → "a mais próxima"
        - "qualquer data", "primeira disponível", "primeira data" → "primeira disponível"
        - "o mais breve possível", "breve possível", "quanto antes" → "quanto antes"
        - "próxima segunda", "segunda feira", "terça" → extrair o dia da semana mencionado
        - IMPORTANTE: Se o usuário mencionar expressões temporais vagas, SEMPRE extraia como uma preferência válida.
    9. ✅ NOVA REGRA PARA NOME DO PACIENTE - Para "patient_name": Extraia o nome da pessoa que será atendida.
        - "Meu nome é João", "Eu sou Maria", "Para João Silva" → extrair o nome mencionado
        - "É para mim", "Quero agendar para mim" → null (aguardar nome específico)
        - "Para minha filha Ana", "Para o José" → extrair "Ana", "José"
        - Seja flexível com variações: "João", "João Silva", "Dr. João" (se for paciente, não médico)
        - Se mencionar apenas "eu", "mim", "comigo" sem nome específico, use null
        - IMPORTANTE: Se o usuário disser "meu nome é X" ou "eu sou X", sempre extrair X como patient_name
    10. Se uma informação não for mencionada ou estiver incerta, use null.
    11. IMPORTANTE: Para "service_type", se não for especificado explicitamente pelo usuário, sempre use "consulta" como padrão.
   
    INFORMAÇÕES A EXTRAIR:
    - "professional_name": Nome do profissional (ex: "Dr. Silva", "Dra. Maria")
    - "specialty": Especialidade médica (ex: "Cardiologia", "Pediatria", "Clínico Geral")
    - "date_preference": Data mencionada (ex: "dia 10", "amanhã", "terça-feira", "a mais próxima")
    - "time_preference": Turno da preferência (DEVE SER "manha" ou "tarde")
    - "specific_time": Horário específico (ex: "08:00", "14:30", "09:00") - FORMATO 24h HH:MM
    - "service_type": Tipo de atendimento (ex: "consulta", "retorno", "exame")
    - "patient_name": Nome do paciente que será atendido (ex: "João Silva", "Maria")
   
    EXEMPLOS DE EXTRAÇÃO:
    Conversa: "Quero marcar consulta com Dr João para Maria Silva"
    → {{ "professional_name": "Dr. João", "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": "consulta", "patient_name": "Maria Silva" }}
   
    Conversa: "Meu nome é Carlos e quero pediatra às 15h do dia 5"
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": "dia 5", "time_preference": "tarde", "specific_time": "15:00", "service_type": null, "patient_name": "Carlos" }}
   
    Conversa: "Eu sou Ana. A especialidade é pediatra. Gostaria de marcar para as 10 da manhã."
    → {{ "professional_name": null, "specialty": "Pediatria", "date_preference": null, "time_preference": "manha", "specific_time": "10:00", "service_type": null, "patient_name": "Ana" }}

    Conversa: "Para minha filha Laura, agendar com Dra. Ana para consulta dia 10 às 09:30."
    → {{ "professional_name": "Dra. Ana", "specialty": null, "date_preference": "dia 10", "time_preference": "manha", "specific_time": "09:30", "service_type": "consulta", "patient_name": "Laura" }}

    ✅ NOVOS EXEMPLOS COM NOME DO PACIENTE:
    Conversa: "Quero agendar para José Silva"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": null, "patient_name": "José Silva" }}
    
    Conversa: "Meu nome é Maria"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": null, "patient_name": "Maria" }}
    
    Conversa: "É para mim" 
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": null, "patient_name": null }}
    
    Conversa: "Quero agendar para Pedro"
    → {{ "professional_name": null, "specialty": null, "date_preference": null, "time_preference": null, "specific_time": null, "service_type": null, "patient_name": "Pedro" }}

    // ... existing code ...
   
    HISTÓRICO COMPLETO DA CONVERSA:
    {conversation_history}
   
    Extraia as informações no seguinte formato JSON, aderindo estritamente às regras de extração acima:
    """
)
