from langchain_core.prompts import ChatPromptTemplate

CLASSIFY_MESSAGE_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Categorize a seguinte consulta do cliente em uma das seguintes categorias:
    - "scheduling"
    - "greeting"
    - "farewell"
    - "fallback_node"
 
    Retorne APENAS o nome da categoria escolhida, sem nenhum texto explicativo, aspas literais ou prefixos como "Categoria:".
 
    Consulta do cliente: {user_query}
    Categoria Selecionada:"""
)
