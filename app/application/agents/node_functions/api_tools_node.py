import logging
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import ToolNode

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.agents.tools.medical_api_tools import MedicalApiTools 
from app.application.interfaces.illm_service import ILLMService 

logger = logging.getLogger(__name__)

TOOL_NODE_NAME = "execute_medical_tools"

def create_api_tool_executor_node(medical_api_tools: MedicalApiTools):
    """
    Cria um ToolNode do LangGraph que pode executar as MedicalApiTools.
    """
    return ToolNode(tools=[
        medical_api_tools.get_available_specialties,
        medical_api_tools.get_professionals_by_specialty
    ])

def create_tool_calling_agent_node(llm_service: ILLMService, medical_api_tools: MedicalApiTools):
    """
    Cria o nó que decide qual ferramenta chamar ou se responde diretamente.
    Este nó efetivamente contém o "agente de chamada de ferramenta".
    """

    llm_chat_client = llm_service.client 

    if not hasattr(llm_chat_client, 'bind_tools'):
         logger.warning("O cliente LLM pode não suportar 'bind_tools' diretamente. Verifique a compatibilidade.")

    tools = [
        medical_api_tools.get_available_specialties,
        medical_api_tools.get_professionals_by_specialty
    ]
    llm_with_tools = llm_chat_client.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um assistente prestativo. Você tem acesso a ferramentas para buscar informações sobre especialidades médicas e profissionais. "
                "Use as ferramentas quando o usuário perguntar sobre especialidades disponíveis ou profissionais de uma especialidade específica. "
                "Se a pergunta não puder ser respondida com as ferramentas, responda diretamente da melhor forma possível. "
                "Se uma ferramenta for chamada, você receberá o resultado dela e então deverá formular uma resposta final para o usuário com base nesse resultado."
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    tool_calling_agent_runnable = prompt | llm_with_tools

    async def agent_node_func(state: MessageAgentState) -> dict:
        logger.info(f"--- Executando nó agente de chamada de ferramenta (agent_node_func) ---")

        agent_inputs = {"messages": state["messages"]} 

        try:
            ai_response_or_tool_call: AIMessage = await tool_calling_agent_runnable.ainvoke(agent_inputs)

            new_messages = state["messages"] + [ai_response_or_tool_call]

            if ai_response_or_tool_call.tool_calls:
                logger.info(f"Agente decidiu chamar ferramenta(s): {ai_response_or_tool_call.tool_calls}")
                return {"messages": new_messages, "next_step": TOOL_NODE_NAME} 
            else:
                logger.info(f"Agente respondeu diretamente: {ai_response_or_tool_call.content[:100]}...")
                return {"messages": new_messages, "next_step": "completed"}

        except Exception as e:
            logger.error(f"Erro no agent_node_func: {e}", exc_info=True)
            error_message = AIMessage(content="Desculpe, tive um problema ao processar sua solicitação com as ferramentas. Como posso ajudar de outra forma?")
            return {"messages": state["messages"] + [error_message], "next_step": "fallback_node"}

    return agent_node_func