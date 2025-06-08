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

    1. **CREATE** - Usuário quer criar um NOVO agendamento ou está fornecendo dados para um agendamento em andamento.
       - Exemplos: "Quero marcar consulta", "Agendar com Dr. Silva", "Pode ser com a Dra. Clara", "Na sexta-feira às 10h"

    2. **UPDATE** - Usuário quer ALTERAR/REMARCAR/CORRIGIR dados de um agendamento já existente ou que ele acredita já estar agendado.
       - Exemplos: "Mudar o horário", "Trocar médico", "Não, quero outro dia", "Corrigir especialidade", "Quero alterar minha consulta", "Quero mudar minha consulta"

    3. **UPDATE_WITHOUT_DATA** - Usuário quer ALTERAR/REMARCAR/CORRIGIR dados de agendamento, mas não há um agendamento ativo na conversa para ser alterado.


    REGRAS DE DECISÃO:
    - **Priorize o fluxo da conversa**: Se a última mensagem da IA foi uma pergunta para coletar dados (ex: "Qual especialidade?"), e a mensagem do usuário parece ser uma resposta a essa pergunta, a intenção é continuar o processo atual. Se o processo é de criação, a intenção é **CREATE**.
    - **CREATE vs UPDATE**: A intenção `CREATE` abrange todo o processo de coleta de dados para um *novo* agendamento. `UPDATE` é para modificar um agendamento que o usuário considera já feito ou em processo de confirmação.
    - **Iniciando a conversa**: Se não há dados de agendamento e o usuário menciona agendar, a intenção é **CREATE**.
    - **Dados existentes**: A presença de alguns dados de agendamento não significa automaticamente que a intenção é `UPDATE`. Avalie se o usuário está adicionando informações para completar um novo agendamento ou explicitamente pedindo para *mudar* algo.
    - **Dúvida com dados existentes**: Na dúvida entre CREATE e UPDATE, se o usuário não usar palavras como "mudar", "alterar", "trocar", "corrigir", prefira **CREATE**.
    - **UPDATE sem dados**: Se o usuário quer explicitamente "alterar" ou "remarcar" mas não há dados de agendamento na conversa, use **UPDATE_WITHOUT_DATA**.


    RESPONDA APENAS COM UMA DAS PALAVRAS (sem aspas, sem explicação):
    CREATE
    UPDATE
    UPDATE_WITHOUT_DATA
    UNCLEAR

    IMPORTANTE:
    - Se a intenção não está clara, responda com UNCLEAR
    - Não inclua aspas na sua resposta
    - Responda apenas a palavra

    """
)