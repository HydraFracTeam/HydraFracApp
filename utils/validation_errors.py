# processing/validation_errors.py

from pydantic import ValidationError


def format_pydantic_error(e: ValidationError) -> str:
    """
    Convert Pydantic ValidationError into a user-friendly message.
    """

    messages = []

    for error in e.errors():

        field = ".".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "")

        if field:
            messages.append(f"{field}: {msg}")
        else:
            messages.append(msg)

    return "; ".join(messages)
