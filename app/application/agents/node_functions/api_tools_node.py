import logging

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import ToolNode

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.agents.tools.medical_api_tools import MedicalApiTools
from app.application.interfaces.illm_service import ILLMService
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

TOOL_NODE_NAME = "execute_medical_tools"


def create_api_tool_executor_node(medical_api_tools: MedicalApiTools):
    """
    Cria um ToolNode do LangGraph que pode executar as MedicalApiTools.
    """
    return ToolNode(
        tools=[
            medical_api_tools.get_available_specialties,
            medical_api_tools.get_professionals_by_specialty,
            medical_api_tools.check_availability,
        ]
    )


def create_tool_calling_agent_node(
    llm_service: ILLMService, medical_api_tools: MedicalApiTools
):
    """
    Cria o nó que decide qual ferramenta chamar ou se responde diretamente.
    Este nó efetivamente contém o "agente de chamada de ferramenta".
    """

    llm_chat_client = llm_service.client

    if not hasattr(llm_chat_client, "bind_tools"):
        logger.warning(
            "O cliente LLM pode não suportar 'bind_tools' diretamente. Verifique a compatibilidade."
        )

    tools = [
        medical_api_tools.get_available_specialties,
        medical_api_tools.get_professionals_by_specialty,
        medical_api_tools.check_availability,
    ]
    llm_with_tools = llm_chat_client.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um assistente prestativo de uma clínica médica. Você tem acesso a ferramentas para buscar informações sobre especialidades médicas, profissionais e datas disponíveis na agenda deles."
                "\n\nCONTEXTO ATUAL DO AGENDAMENTO:"
                "\n- Profissional: {professional_name}"
                "\n- Especialidade: {specialty}"
                "\n- Data preferida: {date_preference}"
                "\n- Turno preferido: {time_preference}"
                "\n\nINSTRUÇÕES IMPORTANTES:"
                "\n- Se perguntarem 'quais especialidades': use get_available_specialties"
                "\n- Se perguntarem 'quais profissionais' SEM especificar especialidade: use get_available_specialties e explique que precisa saber a especialidade para listar os profissionais"
                "\n- Se perguntarem 'quais profissionais de [especialidade específica]': use get_professionals_by_specialty"
                "\n- Se perguntarem sobre agenda/datas/horários: use check_availability"
                "\n\nCOMPORTAMENTO ESPERADO:"
                "\n- Quando alguém perguntar 'quais profissionais?' ou 'que médicos vocês têm?', use get_available_specialties e responda: 'Para que eu possa fornecer a lista de profissionais, preciso saber qual especialidade você está procurando. Veja as especialidades disponíveis: [lista]. Qual especialidade você deseja?'"
                "\n\nINSTRUÇÕES COMPLEMENTARES:"
                "\n- Se o contexto tem uma especialidade definida mas não tem profissional, use automaticamente 'get_professionals_by_specialty' com a especialidade do contexto."
                "\n- Se o usuário perguntar sobre datas/horários disponíveis e você já tem o nome do profissional no contexto, use 'check_availability' com essas informações."
                "\n- Se o contexto tem informações relevantes (profissional, data, turno), sempre passe elas para as tools."
                "\n- Seja proativo: quando souber a especialidade, busque automaticamente os profissionais."
                "\n\nSe uma ferramenta for chamada, você receberá o resultado dela e então deverá formular uma resposta final para o usuário com base nesse resultado.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    tool_calling_agent_runnable = prompt | llm_with_tools

    async def agent_node_func(state: MessageAgentState) -> dict:
        """
        Função do nó agente que decide qual ferramenta chamar.
        """
        logger.info("--- Executando nó agent_tool_caller ---")

        messages = state.get("messages", [])
        conversation_context = state.get("conversation_context", "")
        
        # 🆕 RESPOSTA PERSONALIZADA: Quando vem de incerteza do usuário
        if conversation_context == "uncertainty_help":
            logger.info("🎯 CONTEXTO DE AJUDA: Gerando resposta personalizada para incerteza")
            
            try:
                # Obter introdução amigável
                llm_service = LLMFactory.create_llm_service("openai")
                intro_message = llm_service.generate_helpful_specialties_intro()
                
                # Chamar a ferramenta de especialidades
                specialties_result = await medical_api_tools.get_available_specialties.ainvoke({})
                
                # Combinar introdução personalizada + lista de especialidades
                # Extrair apenas a lista da resposta da ferramenta (remover a parte formal)
                if "Encontrei as seguintes especialidades" in specialties_result:
                    # Pegar apenas a parte da lista
                    specialties_list = specialties_result.split("Encontrei as seguintes especialidades médicas disponíveis na clínica:\n")[1]
                    # Remover a pergunta final também
                    if "Você gostaria de ver" in specialties_list:
                        specialties_list = specialties_list.split("\n\nVocê gostaria de ver")[0]
                    
                    # Combinar introdução personalizada + lista
                    combined_response = f"{intro_message}\n\n{specialties_list}\n\nQual dessas especialidades você gostaria de consultar?"
                else:
                    # Fallback se não conseguir extrair
                    combined_response = f"{intro_message}\n\n{specialties_result}"
                
                ai_message = AIMessage(content=combined_response)
                return {
                    "messages": state["messages"] + [ai_message],
                    "next_step": "completed",
                    "conversation_context": "specialty_shown",
                }
                
            except Exception as e:
                logger.error(f"Erro ao gerar resposta personalizada: {e}", exc_info=True)
                # Fallback para resposta padrão
                fallback_message = "Sem problemas! Deixe-me mostrar as especialidades que temos disponíveis."
                ai_message = AIMessage(content=fallback_message)
                return {
                    "messages": state["messages"] + [ai_message],
                    "next_step": "agent_tool_caller",  # Tentar novamente
                }

        extracted_details = state.get("extracted_scheduling_details")
        conversation_context = state.get("conversation_context")

        context_info = {
            "professional_name": (
                extracted_details.professional_name
                if extracted_details
                else "Não definido"
            ),
            "specialty": (
                extracted_details.specialty if extracted_details else "Não definida"
            ),
            "date_preference": (
                extracted_details.date_preference
                if extracted_details
                else "Não definida"
            ),
            "time_preference": (
                extracted_details.time_preference
                if extracted_details
                else "Não definido"
            ),
        }

        logger.info(f"Contexto atual para tools: {context_info}")
        logger.info(f"Conversation context: {conversation_context}")

        # 🆕 OBTER a última mensagem PRIMEIRO
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        # 🆕 DETECTAR se a tool está mostrando datas alternativas
        if isinstance(last_message, ToolMessage):
            if (
                "📅 Datas disponíveis:" in last_message.content
                and "Qual data você prefere?" in last_message.content
            ):
                logger.info(
                    "Tool mostrou datas alternativas - configurando contexto para seleção"
                )

                # 🆕 CONVERTER ToolMessage para AIMessage para aparecer no chat
                ai_message = AIMessage(content=last_message.content)

                return {
                    "messages": state["messages"] + [ai_message],
                    "conversation_context": "awaiting_date_selection",
                    "next_step": "completed",
                }

            # 🔧 CONTINUA com o código existente...
            details = state.get("extracted_scheduling_details")
            if details and all(
                [
                    details.professional_name,
                    details.specialty,
                    details.date_preference,
                    details.time_preference,
                    details.service_type,
                ]
            ):
                logger.info(
                    "Tool executada e todos os detalhes estão preenchidos. Avançando para validação."
                )
                ai_message = AIMessage(
                    content="Ok, encontrei as informações. Vamos confirmar os dados para o seu agendamento."
                )
                return {
                    "messages": state["messages"] + [ai_message],
                    "next_step": "validate_and_confirm",
                }

        # Resto da lógica existente do specialty_selection...
        if (
            conversation_context == "specialty_selection"
            and extracted_details
            and extracted_details.specialty
        ):
            logger.info(
                f"🎯 AUTOMÁTICO: Chamando get_professionals_by_specialty para '{extracted_details.specialty}'"
            )
            try:
                tool_result = (
                    await medical_api_tools.get_professionals_by_specialty.ainvoke(
                        {"specialty_name": extracted_details.specialty}
                    )
                )
                logger.info(f"Tool result: {tool_result}")

                ai_message = AIMessage(content=tool_result)

                return {
                    "messages": state["messages"] + [ai_message],
                    "next_step": "completed",
                }

            except Exception as e:
                logger.error(f"Erro ao chamar tool automaticamente: {e}", exc_info=True)
                error_message = AIMessage(
                    content=f"Desculpe, tive um problema ao buscar os profissionais de {extracted_details.specialty}. Você pode me dizer o nome de um profissional específico?"
                )
                return {
                    "messages": state["messages"] + [error_message],
                    "next_step": "completed",
                }

        agent_inputs = {"messages": state["messages"], **context_info}

        try:
            ai_response_or_tool_call: AIMessage = (
                await tool_calling_agent_runnable.ainvoke(agent_inputs)
            )

            if ai_response_or_tool_call.tool_calls:
                for tool_call in ai_response_or_tool_call.tool_calls:
                    if tool_call["name"] == "check_availability" and extracted_details:
                        args = tool_call["args"]
                        if (
                            not args.get("professional_name")
                            and extracted_details.professional_name
                        ):
                            args["professional_name"] = (
                                extracted_details.professional_name
                            )
                        if not args.get("date") and extracted_details.date_preference:
                            args["date"] = extracted_details.date_preference
                        if (
                            not args.get("time_period")
                            and extracted_details.time_preference
                        ):
                            args["time_period"] = extracted_details.time_preference

                        logger.info(
                            f"Argumentos da tool check_availability enriquecidos: {args}"
                        )

            new_messages = state["messages"] + [ai_response_or_tool_call]

            if ai_response_or_tool_call.tool_calls:
                logger.info(
                    f"Agente decidiu chamar ferramenta(s): {ai_response_or_tool_call.tool_calls}"
                )
                return {"messages": new_messages, "next_step": TOOL_NODE_NAME}
            else:
                logger.info(
                    f"Agente respondeu diretamente: {ai_response_or_tool_call.content[:100]}..."
                )
                return {"messages": new_messages, "next_step": "completed"}

        except Exception as e:
            logger.error(f"Erro no agent_node_func: {e}", exc_info=True)
            error_message = AIMessage(
                content="Desculpe, tive um problema ao processar sua solicitação com as ferramentas. Como posso ajudar de outra forma?"
            )
            return {
                "messages": state["messages"] + [error_message],
                "next_step": "fallback_node",
            }

    return agent_node_func
