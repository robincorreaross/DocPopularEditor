"""
date_manager.py - Utilitários para formatação e máscara de datas (PySide6).
Portado do DocPopular para o DocPopularEditor.
"""


def format_date_br_to_iso(date_str: str) -> str:
    """Converte DD/MM/AAAA para AAAA-MM-DD."""
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return ""


def format_iso_to_date_br(iso_str: str) -> str:
    """Converte AAAA-MM-DD para DD/MM/AAAA."""
    try:
        parts = iso_str.split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return ""
