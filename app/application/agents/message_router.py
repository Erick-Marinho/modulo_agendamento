class MessageRouter:
   def route_orquestrator(self, state):
        next_step = state.get("next_step").lower()

        if "scheduling" in next_step:
            return "scheduling"
        elif "greeting" in next_step:
            return "greeting"
        elif "farewell" in next_step:
            return "farewell"
        else:
            return "fallback_node"
