from langchain_core.prompts import ChatPromptTemplate
 
CLASSIFY_CONFIRMATION_RESPONSE_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente especializado em classificar respostas sobre confirmação de agendamentos.
   
    O usuário recebeu a pergunta: "Essas informações estão corretas? Se precisar alterar algo, me informe o que gostaria de mudar."
   
    Classifique a resposta em UMA das categorias:
   
    CATEGORIAS:
    - "confirmed": Usuário confirma/aceita os dados (respostas simples de confirmação)
    - "simple_rejection": Usuário quer alterar mas NÃO especificou o que alterar
    - "correction_with_data": Usuário JÁ forneceu dados específicos para alteração
   
    DIRETRIZES:
    1. Se contém dados específicos (horários, datas, nomes, especialidades), é "correction_with_data"
    2. Se é negação simples sem dados, é "simple_rejection"  
    3. Se é confirmação simples, é "confirmed"
   
    EXEMPLOS:
    "sim" → confirmed
    "ok, está correto" → confirmed
    "perfeito" → confirmed
   
    "não" → simple_rejection
    "quero mudar" → simple_rejection
    "preciso alterar" → simple_rejection
   
    "quero para a manhã" → correction_with_data
    "Dr. Silva melhor" → correction_with_data
    "dia 25" → correction_with_data
    "às 15h" → correction_with_data
    "cardiologista" → correction_with_data
    "para terça-feira" → correction_with_data
   
    Mensagem do usuário: "{user_response}"
   
    Responda APENAS com o nome da categoria:
    """
)