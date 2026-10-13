import unicodedata


def normalizar_texto(texto: str) -> str:
    """Lowercase text, remove accents, and collapse repeated whitespace."""
    if not texto:
        return ""

    texto_normalizado = str(texto).strip().lower()
    texto_sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto_normalizado)
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(texto_sin_acentos.split())
