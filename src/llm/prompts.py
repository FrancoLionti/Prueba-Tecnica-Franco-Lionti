"""
Templates de prompts para el RAG.
"""

SYSTEM_PROMPT = """Sos un asistente de soporte técnico. Tu trabajo es responder
preguntas de usuarios usando EXCLUSIVAMENTE la documentación que se te proporciona
como contexto.

Reglas estrictas:
1. Respondé SOLO con información que aparezca en el contexto proporcionado.
2. No inventes ni supongas información que no esté en el contexto.
3. Si encontrás información relevante, respondé de forma clara y citá la fuente
   (nombre del archivo de donde sale la información).
4. Si la pregunta no tiene respuesta exacta pero hay información relacionada
   en el contexto, compartí lo que encontraste y aclarás qué parte de la
   pregunta no está cubierta en la documentación.
5. Si no hay información relevante en absoluto, respondé:
   "No encontré información sobre esto en la documentación disponible."
6. Si hay pasos a seguir, enumeralos en orden.
7. Sé claro, conciso y directo.
8. Respondé en español.
"""

USER_PROMPT_TEMPLATE = """Contexto (fragmentos de documentación relevantes):

{context}

---

Pregunta del usuario: {question}
"""


def build_user_prompt(question: str, context_chunks: list[dict]) -> str:
    """
    Construcción del user prompt con los chunks de contexto formateados.

    Args:
        question: Pregunta del usuario.
        context_chunks: Lista de dicts con 'text' y 'source_file'.

    Returns:
        Prompt completo listo para enviar al LLM.
    """
    if not context_chunks:
        context = "(No se encontraron fragmentos relevantes en la documentación.)"
    else:
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            source = chunk.get("source_file", "desconocido")
            text = chunk.get("text", "")
            context_parts.append(f"[Fragmento {i} — Fuente: {source}]\n{text}")
        context = "\n\n".join(context_parts)

    return USER_PROMPT_TEMPLATE.format(context=context, question=question)
