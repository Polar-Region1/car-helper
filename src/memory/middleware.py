from langchain.agents.middleware import dynamic_prompt

from src.prompts.system_prompt import SYSTEM_PROMPT


def build_system_prompt(memory_context: str):
    if not memory_context:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT.rstrip()}\n\n{memory_context}\n"


@dynamic_prompt
def memory_aware_prompt(request):
    context = request.runtime.context
    memory_context = context.memory_context if context else ""
    return build_system_prompt(memory_context)
