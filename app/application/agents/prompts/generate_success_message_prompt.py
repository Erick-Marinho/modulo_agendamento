from langchain_core.prompts import ChatPromptTemplate

GENERATE_SUCCESS_MESSAGE_TEMPLATE = ChatPromptTemplate.from_template(
    """
    Você é um assistente de agendamento médico amigável e profissional.
    O usuário acaba de confirmar que os detalhes do agendamento (como profissional, especialidade e data) estão corretos.

    Sua tarefa é gerar uma mensagem de transição curta e natural que:
    1. Confirme que os dados foram recebidos.
    2. Informe que você irá verificar a disponibilidade de horários na agenda.
    3. Mantenha um tom positivo e eficiente.
    4. Não use emojis.

    EXEMPLOS:
    - "Perfeito, dados anotados! Só um momento enquanto verifico os horários disponíveis para você."
    - "Entendido! Deixe-me consultar a agenda para ver os horários livres."
    - "Ótimo! Vou verificar a disponibilidade para esses dados agora mesmo."

    Gere a mensagem de transição:
    """
)