import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from coleta.config import Config
from coleta.http import (BloqueadoPorRobots, Cliente, ErroDeColeta,
                         RobotsIndisponivel)


def cliente_com_robots(config, dormidas=None):
    esperas = [] if dormidas is None else dormidas
    cliente = Cliente(config, dormir=esperas.append)
    cliente.carregar_robots()
    return cliente, esperas


def test_le_o_crawl_delay_do_robots(config):
    from dataclasses import replace
    cliente, _ = cliente_com_robots(replace(config, espera=None))
    assert cliente.espera == 1.0


def test_espera_configurada_ganha_do_robots(config):
    from dataclasses import replace
    cliente, _ = cliente_com_robots(replace(config, espera=0.25))
    assert cliente.espera == 0.25


def test_pagina_permitida_e_baixada(config):
    cliente, _ = cliente_com_robots(config)
    assert cliente.obter(config.base_url + "/vagas/").status_code == 200


def test_pagina_proibida_pelo_robots_nem_e_pedida(config, site):
    cliente, _ = cliente_com_robots(config)
    with pytest.raises(BloqueadoPorRobots):
        cliente.obter(site + "/interno/relatorio")
    assert cliente.pedidos == 0


def test_agente_banido_nao_coleta_nada(config):
    from dataclasses import replace
    cliente, _ = cliente_com_robots(replace(config, user_agent="BotAbusivo/1.0"))
    assert not cliente.pode(config.base_url + "/vagas/")


def test_503_e_repetido_ate_funcionar(config, site):
    cliente, esperas = cliente_com_robots(config)
    chave = uuid.uuid4().hex
    resposta = cliente.obter(f"{site}/instavel/vagas?chave={chave}&falhas=2")
    assert resposta.status_code == 200
    assert cliente.repeticoes == 2
    # o servidor pede Retry-After: 1, que vale mais que os 0,5 s do cálculo
    assert esperas[0] == 1.0
    assert 1.0 <= esperas[1] <= 1.1 + 1e-9


def test_espera_cresce_o_dobro_a_cada_tentativa(config):
    cliente = Cliente(config)
    for tentativa, base in [(1, 0.5), (2, 1.0), (3, 2.0), (4, 4.0)]:
        espera = cliente._espera_da_tentativa(tentativa, None)
        assert base <= espera <= base * 1.1 + 1e-9


def test_espera_nunca_passa_do_maximo(config):
    cliente = Cliente(config)
    assert cliente._espera_da_tentativa(20, None) <= 30.0 * 1.1 + 1e-9
    assert cliente._espera_da_tentativa(1, "9999") == 30.0


def test_retry_after_invalido_e_ignorado(config):
    cliente = Cliente(config)
    espera = cliente._espera_da_tentativa(1, "Wed, 21 Oct 2026 07:28:00 GMT")
    assert 0.5 <= espera <= 0.55 + 1e-9


def test_429_respeita_o_retry_after(config, site):
    cliente, esperas = cliente_com_robots(config)
    for _ in range(3):
        cliente.obter(site + "/limitado/vagas")
    with pytest.raises(ErroDeColeta, match="429"):
        cliente.obter(site + "/limitado/vagas")
    assert esperas and all(e >= 2.0 for e in esperas)


def test_404_nao_e_repetido(config, site):
    cliente, esperas = cliente_com_robots(config)
    with pytest.raises(ErroDeColeta, match="404"):
        cliente.obter(site + "/vagas/v999")
    assert cliente.repeticoes == 0 and esperas == []


def test_timeout_vira_erro_de_coleta_depois_das_tentativas(config, site):
    from dataclasses import replace
    rapido = replace(config, timeout=(1.0, 0.3), max_tentativas=2)
    cliente, esperas = cliente_com_robots(rapido)
    with pytest.raises(ErroDeColeta, match="Timeout"):
        cliente.obter(site + "/lento")
    assert len(esperas) == 1


def test_espera_entre_pedidos(config, site):
    from dataclasses import replace
    cliente, esperas = cliente_com_robots(replace(config, espera=2.0))
    cliente.obter(site + "/vagas/")
    cliente.obter(site + "/vagas/?pagina=2")
    assert esperas and 0 < esperas[0] <= 2.0


def servidor_de_robots(codigo):
    class M(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(codigo)
            self.send_header("Content-Length", "0")
            self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), M)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_sem_robots_txt_tudo_e_permitido():
    srv = servidor_de_robots(404)
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        cliente = Cliente(Config(base_url=base, espera=0.0))
        cliente.carregar_robots()
        assert cliente.pode(base + "/qualquer/coisa")
    finally:
        srv.shutdown()


def test_robots_com_erro_de_servidor_bloqueia_a_coleta():
    srv = servidor_de_robots(503)
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        with pytest.raises(RobotsIndisponivel):
            Cliente(Config(base_url=base, espera=0.0)).carregar_robots()
    finally:
        srv.shutdown()


def test_site_fora_do_ar_e_robots_indisponivel():
    with pytest.raises(RobotsIndisponivel):
        Cliente(Config(base_url="http://127.0.0.1:9", espera=0.0)).carregar_robots()
