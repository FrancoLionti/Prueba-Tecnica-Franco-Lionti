"""
Generador de respuestas usando OpenAI API.

Recibe la pregunta del usuario y los chunks de contexto recuperados
del vector store, arma el prompt y llama a la API de chat de OpenAI
para generar una respuesta fundamentada en la documentación.
"""

from openai import OpenAI, APIError, RateLimitError, APIConnectionError

from src.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL
from src.llm.prompts import SYSTEM_PROMPT, build_user_prompt


# Cliente de OpenAI — se inicializa una sola vez
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Singleton del cliente OpenAI."""
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY no está configurada. "
                "Agregala al archivo .env"
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def generate_answer(
    question: str,
    context_chunks: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> dict:

    """
    Genera una respuesta usando el LLM con los chunks de contexto.

    Args:
        question: Pregunta del usuario.
        context_chunks: Lista de dicts con 'text', 'source_file', 'relevance'.
        model: Modelo a usar (por defecto el de config.py).
        temperature: Aleatoriedad de la respuesta (0.2 = conservador).
        max_tokens: Límite de tokens en la respuesta.

    Returns:
        Dict con 'answer', 'model', 'usage'.

    Raises:
        ValueError: Si la API key no está configurada.
        RuntimeError: Si hay un error en la llamada a la API.
    """
    client = _get_client()
    model = model or OPENAI_CHAT_MODEL

    # Armar el prompt con el contexto
    user_prompt = build_user_prompt(question, context_chunks)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        answer = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        } if response.usage else {}

        return {
            "answer": answer.strip(),
            "model": model,
            "usage": usage,
        }

    except RateLimitError as e:
        raise RuntimeError(
            "OpenAI API: sin cuota disponible. "
            "Verificar que la API Key tenga saldo suficiente."
        ) from e
    except APIConnectionError as e:
        raise RuntimeError(
            "No se pudo conectar a la API de OpenAI. "
            "Verificar la conexión a internet."
        ) from e
    except APIError as e:
        raise RuntimeError(f"Error de OpenAI API: {e.message}") from e
