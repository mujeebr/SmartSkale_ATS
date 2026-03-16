"""Small helper to keep legacy call-sites decoupled from the DI container."""


def get_llm_response(prompt: str) -> str:
    """Forward a prompt to the configured LLM client and return its response."""
    from src.container import get_llm_client

    return get_llm_client().generate(prompt)
