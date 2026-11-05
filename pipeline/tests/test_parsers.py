from bs4 import BeautifulSoup

from coleta import parsers

CARTAO = """
<article class="vaga" data-id="x9">
  <h2 class="titulo"><a href="/vagas/x9">Dev Teste</a></h2>
  <p class="empresa">Empresa Fictícia</p>
  <span class="salario">A combinar</span>
  <time datetime="2026-10-01">01/10/2026</time>
  <ul class="tags"><li>python</li><li>sql</li></ul>
</article>
"""


def test_le_um_cartao_completo():
    sopa = BeautifulSoup(CARTAO, "lxml")
    bruto = parsers.ler_cartao_vaga(sopa.select_one("article"),
                                    "http://site/vagas/")
    assert bruto["id_externo"] == "x9"
    assert bruto["titulo"] == "Dev Teste"
    assert bruto["url"] == "http://site/vagas/x9"
    assert bruto["publicada"] == "2026-10-01"
    assert bruto["tags"] == ["python", "sql"]


def test_campos_ausentes_viram_none_e_nao_quebram():
    sopa = BeautifulSoup(CARTAO, "lxml")
    bruto = parsers.ler_cartao_vaga(sopa.select_one("article"), "http://s/v/")
    assert bruto["local"] is None
    assert bruto["modalidade"] is None


def test_cartao_sem_link_e_sem_data():
    sopa = BeautifulSoup('<article class="vaga" data-id="y"></article>', "lxml")
    bruto = parsers.ler_cartao_vaga(sopa.select_one("article"), "http://s/")
    assert bruto["titulo"] is None and bruto["url"] is None
    assert bruto["publicada"] is None


def test_proxima_pagina():
    com = BeautifulSoup('<a rel="next" href="?pagina=2">Próxima</a>', "lxml")
    sem = BeautifulSoup("<p>fim</p>", "lxml")
    assert parsers.proxima_pagina(com, "http://s/vagas/") == (
        "http://s/vagas/?pagina=2")
    assert parsers.proxima_pagina(sem, "http://s/vagas/") is None
