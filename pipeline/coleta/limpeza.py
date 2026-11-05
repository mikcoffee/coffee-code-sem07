"""Limpeza: do texto da página para dados que um banco aceita."""
import re
from datetime import datetime
from decimal import Decimal

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5,
         "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
         "novembro": 11, "dezembro": 12}

_DINHEIRO = re.compile(r"R\$\s*(\d[\d.]*(?:,\d{1,2})?)")
_DATA_LONGA = re.compile(r"(\d{1,2}) de (\w+) de (\d{4}),\s*(\d{1,2})h(\d{2})")


def limpar_texto(texto: str | None) -> str | None:
    """Tira espaços repetidos e quebras de linha. Vazio vira None."""
    if texto is None:
        return None
    limpo = " ".join(texto.split())
    return limpo or None


def para_centavos(valor: str) -> int:
    """'7.000' vira 700000 e '3.200,50' vira 320050 (inteiros, sem float)."""
    numero = Decimal(valor.replace(".", "").replace(",", "."))
    return int(numero * 100)


def parse_faixa_salarial(texto: str | None) -> tuple[int | None, int | None]:
    """Devolve (mínimo, máximo) em centavos. Sem valor: (None, None)."""
    if not texto:
        return (None, None)
    valores = [para_centavos(v) for v in _DINHEIRO.findall(texto)]
    if not valores:
        return (None, None)
    if len(valores) == 1:
        if texto.strip().lower().startswith("até"):
            return (None, valores[0])
        return (valores[0], valores[0])
    return (min(valores), max(valores))


def parse_local(texto: str | None) -> tuple[str | None, str | None]:
    """'Curitiba, PR' vira ('Curitiba', 'PR'). 'Remoto' vira (None, None)."""
    texto = limpar_texto(texto)
    if not texto or "," not in texto:
        return (None, None)
    cidade, uf = (parte.strip() for parte in texto.rsplit(",", 1))
    return (cidade, uf.upper())


def parse_data_evento(texto: str | None) -> str | None:
    """'sábado, 17 de outubro de 2026, 14h00' vira '2026-10-17T14:00'."""
    achou = _DATA_LONGA.search(texto or "")
    if not achou:
        return None
    dia, mes, ano, hora, minuto = achou.groups()
    numero_mes = MESES.get(mes.lower())
    if numero_mes is None:
        return None
    try:
        momento = datetime(int(ano), numero_mes, int(dia), int(hora), int(minuto))
    except ValueError:                  # 30 de fevereiro, 25h00...
        return None
    return momento.isoformat(timespec="minutes")


def parse_preco(texto: str | None) -> tuple[int | None, int | None]:
    """Devolve (preço, preço para estudantes) em centavos. 'Gratuito' vale 0."""
    texto = limpar_texto(texto) or ""
    if texto.lower().startswith("gratuito"):
        return (0, None)
    valores = [para_centavos(v) for v in _DINHEIRO.findall(texto)]
    if not valores:
        return (None, None)
    return (valores[0], valores[1] if len(valores) > 1 else None)
