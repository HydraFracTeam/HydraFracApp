from pydantic import ValidationError


def format_pydantic_error(e: Exception) -> str:
    """
    Convert ValidationError or ValueError into a user-friendly message.
    """

    # Обработка ошибок pydantic
    if isinstance(e, ValidationError):

        messages = []

        for error in e.errors():

            field = ".".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg", "")
            msg = msg.replace("Value error,", "").strip()

            if field:
                messages.append(f"{field}: {msg}")
            else:
                messages.append(msg)

        return ";\n".join(messages)

    # Обработка обычных ValueError
    if isinstance(e, ValueError):
        return str(e)

    # fallback для любых других ошибок
    return f"Unexpected error: {str(e)}"
