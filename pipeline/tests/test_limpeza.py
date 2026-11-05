import pytest

from coleta import limpeza


@pytest.mark.parametrize("texto, esperado", [
    ("R$ 7.000 a R$ 9.500", (700000, 950000)),
    ("R$ 4.500", (450000, 450000)),
    ("R$ 3.200,50", (320050, 320050)),
    ("até R$ 11.000", (None, 1100000)),
    ("A combinar", (None, None)),
    ("R$ .", (None, None)),
    ("", (None, None)),
    (None, (None, None)),
])
def test_faixa_salarial(texto, esperado):
    assert limpeza.parse_faixa_salarial(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("Curitiba, PR", ("Curitiba", "PR")),
    ("São José dos Pinhais, PR", ("São José dos Pinhais", "PR")),
    ("Remoto", (None, None)),
    ("Online", (None, None)),
    (None, (None, None)),
])
def test_local(texto, esperado):
    assert limpeza.parse_local(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("sábado, 17 de outubro de 2026, 14h00", "2026-10-17T14:00"),
    ("quinta-feira, 22 de outubro de 2026, 19h30", "2026-10-22T19:30"),
    ("sexta-feira, 6 de novembro de 2026, 08h30", "2026-11-06T08:30"),
    ("sábado, 5 de dezembro de 2026, 14h00", "2026-12-05T14:00"),
    ("sem data nenhuma", None),
    ("quinta, 30 de fevereiro de 2026, 10h00", None),
    ("sábado, 5 de maio de 2026, 25h00", None),
    ("1 de marteiro de 2026, 10h00", None),
    (None, None),
])
def test_data_do_evento(texto, esperado):
    assert limpeza.parse_data_evento(texto) == esperado


def test_data_com_mes_de_acento():
    assert limpeza.parse_data_evento("quarta, 4 de março de 2026, 9h05") == (
        "2026-03-04T09:05")


@pytest.mark.parametrize("texto, esperado", [
    ("Gratuito", (0, None)),
    ("R$ 40,00", (4000, None)),
    ("R$ 120,00 (estudantes: R$ 60,00)", (12000, 6000)),
    ("sob consulta", (None, None)),
])
def test_preco(texto, esperado):
    assert limpeza.parse_preco(texto) == esperado


def test_limpar_texto():
    assert limpeza.limpar_texto("  Dev   Python \n Júnior ") == "Dev Python Júnior"
    assert limpeza.limpar_texto("   ") is None
    assert limpeza.limpar_texto(None) is None


def test_dinheiro_em_centavos_nao_usa_float():
    assert limpeza.para_centavos("0,10") + limpeza.para_centavos("0,20") == 30
