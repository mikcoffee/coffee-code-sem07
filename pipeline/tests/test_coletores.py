from coleta import coletores
from coleta.config import Config

HTML = """<html><body><ul class="eventos">
<li class="evento" data-id="e1"><h3><a href="/eventos/e1">Bom</a></h3>
<p class="quando">sábado, 17 de outubro de 2026, 14h00</p><p class="onde">Online</p>
<p class="preco">Gratuito</p><p class="organizacao">X</p></li>
<li class="evento" data-id="e2"><h3><a href="/eventos/e2">Data impossível</a></h3>
<p class="quando">quinta, 30 de fevereiro de 2026, 10h00</p><p class="onde">Curitiba, PR</p>
<p class="preco">R$ 40,00</p><p class="organizacao">Y</p></li>
</ul></body></html>""".encode("utf-8")


class Resposta:
    content = HTML


class ClienteFalso:
    def obter(self, url, params=None):
        return Resposta()


def test_evento_com_data_impossivel_e_guardado_e_avisado():
    resultado = coletores.coletar_eventos(ClienteFalso(), Config())
    bons = {e.id_externo: e for e in resultado.itens}
    assert bons["e1"].inicio == "2026-10-17T14:00" and bons["e1"].online == 1
    assert bons["e2"].inicio is None
    assert resultado.erros == ["evento sem data legível: e2"]
    assert resultado.completo


# ---------------------------------------------------------------- vagas
from falsos import CARTAO, ClienteDePaginas, pagina  # noqa: E402
from coleta.http import BloqueadoPorRobots, ErroDeColeta  # noqa: E402


def test_paginacao_em_ciclo_deixa_a_coleta_incompleta():
    lista = pagina(CARTAO.format(i="x1", titulo="T"), proxima="/vagas/")
    resultado = coletores.coletar_vagas(ClienteDePaginas(lista), Config())
    assert resultado.completo is False
    assert "ciclo detectado na paginação" in resultado.erros


def test_vaga_que_existe_mas_veio_quebrada_deixa_a_coleta_incompleta():
    lista = pagina(CARTAO.format(i="x2", titulo=""))     # link sem texto
    resultado = coletores.coletar_vagas(ClienteDePaginas(lista), Config())
    assert resultado.itens == []
    assert resultado.erros == ["vaga inválida: x2"]
    assert resultado.completo is False


def test_evento_invalido_deixa_a_coleta_incompleta():
    class Evt(ClienteDePaginas):
        def obter(self, url, params=None):
            return type("R", (), {"content": b'<li class="evento" '
                                  b'data-id="e1"><p class="quando">?</p></li>'})()

    resultado = coletores.coletar_eventos(Evt(""), Config())
    assert resultado.erros == ["evento inválido: e1"]
    assert resultado.completo is False


def test_cartao_sem_link_nao_derruba_o_coletor():
    lista = pagina('<article class="vaga" data-id="x3"><p>sem link</p></article>')
    resultado = coletores.coletar_vagas(ClienteDePaginas(lista), Config())
    assert resultado.erros == ["vaga inválida: x3"]
    assert resultado.completo is False


def test_detalhe_bloqueado_pelo_robots_interrompe_tudo():
    lista = pagina(CARTAO.format(i="x4", titulo="T"))
    cliente = ClienteDePaginas(lista, BloqueadoPorRobots("proibido"))
    try:
        coletores.coletar_vagas(cliente, Config())
    except BloqueadoPorRobots:
        return
    raise AssertionError("deveria ter interrompido a coleta")


def test_falha_no_detalhe_marca_o_campo_como_indisponivel():
    lista = pagina(CARTAO.format(i="x5", titulo="T"))
    cliente = ClienteDePaginas(lista, ErroDeColeta("503"))
    resultado = coletores.coletar_vagas(cliente, Config())
    assert resultado.completo is True
    assert resultado.itens[0].indisponiveis == ("descricao",)
    assert resultado.erros == ["503"]
