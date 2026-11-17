"""Normalización y validación local de identidad mexicana (sin consulta externa)."""
import re
from datetime import date

PARTICULAS = {"de", "del", "la", "las", "los", "y"}
ESTADOS_CURP = set("AS BC BS CC CL CM CS CH DF DG GT GR HG JC MC MN MS NT NL OC PL QT QR SP SL SR TC TS TL VZ YN ZS NE".split())
CURP_RE = re.compile(r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HMX](?:AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$")
RFC_PF_RE = re.compile(r"^[A-Z&Ñ]{4}\d{6}[A-Z0-9]{3}$")


def normalizar_palabras(value):
    words = re.sub(r"\s+", " ", str(value or "")).strip().lower().split(" ")
    result = []
    for i, word in enumerate(words):
        if not word:
            continue
        if word in PARTICULAS:
            result.append(word)
        else:
            result.append(word[:1].upper() + word[1:])
    return " ".join(result)


def _fecha_curp(value):
    yy, mm, dd = int(value[4:6]), int(value[6:8]), int(value[8:10])
    year = 2000 + yy if value[16].isdigit() else 1900 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def validar_curp(value, nacimiento=None):
    curp = str(value or "").strip().upper()
    if not CURP_RE.fullmatch(curp):
        return False
    birth = _fecha_curp(curp)
    if birth is None:
        return False
    # Dígito verificador oficial: mapa alfanumérico, pesos 18..2.
    alphabet = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
    try:
        total = sum(alphabet.index(char) * (18 - i) for i, char in enumerate(curp[:17]))
    except ValueError:
        return False
    if (10 - total % 10) % 10 != int(curp[17]):
        return False
    if nacimiento:
        try:
            parsed = date.fromisoformat(str(nacimiento)[:10])
        except ValueError:
            return False
        if parsed != birth:
            return False
    return True


def validar_rfc_persona_fisica(value):
    rfc = str(value or "").strip().upper()
    if not RFC_PF_RE.fullmatch(rfc):
        return False
    raw = rfc[4:10]
    yy, mm, dd = int(raw[:2]), int(raw[2:4]), int(raw[4:6])
    for century in (1900, 2000):
        try:
            date(century + yy, mm, dd)
            return True
        except ValueError:
            continue
    return False
