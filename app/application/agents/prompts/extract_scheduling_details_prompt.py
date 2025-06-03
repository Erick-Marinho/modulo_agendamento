from langchain_core.prompts import ChatPromptTemplate

EXTRACT_SCHEDULING_DETAILS_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente IA perito em analisar DIÁLOGOS sobre agendamento de consultas.
    Sua tarefa é extrair as seguintes informações do HISTÓRICO DA CONVERSA fornecido, considerando todas as mensagens trocadas para obter os dados mais atualizados e completos.
    Se o usuário corrigir uma informação anterior, a correção no diálogo é a que prevalece.

    Informações a serem extraídas:
    - "professional_name": O nome completo do profissional de saúde mencionado. (Ex: "Dra. Clara Joaquina", "Dr. João Carlos")
    - "specialty": A especialidade médica desejada. (Ex: "Cardiologia", "Pediatra")
    - "date_preference": Qualquer menção a uma data ou período. (Ex: "amanhã", "dia 10", "próxima terça", "15/06/2025")
    - "time_preference": Qualquer menção a um horário. (Ex: "10h", "pela manhã", "final da tarde", "às 14:30")
    - "service_type": O tipo de serviço, se especificado. (Ex: "consulta", "retorno", "exame de sangue")

    Se uma informação não for mencionada em NENHUMA parte do diálogo ou não estiver clara, utilize o valor null para o campo correspondente.

    HISTÓRICO DA CONVERSA (entre Usuário e Assistente):
    {conversation_history}

    JSON com as informações extraídas de TODO o histórico:
    """
)