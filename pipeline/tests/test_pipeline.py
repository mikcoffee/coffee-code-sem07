import os
import sqlite3

from coleta import banco, executar
from coleta.http import Cliente, ErroDeColeta


def consultar(config, sql, *params):
    conn = sqlite3.connect(config.banco)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def rodar(config, fontes=("vagas", "eventos"), cliente=None):
    return executar.executar(config, fontes, cliente)


def test_primeira_execucao_grava_vagas_e_eventos(config):
    assert rodar(config) == executar.SUCESSO
    assert consultar(config, "SELECT count(*) FROM vagas")[0][0] == 20
    assert consultar(config, "SELECT count(*) FROM eventos")[0][0] == 8


def test_executar_de_novo_nao_duplica_nada(config):
    rodar(config)
    assert rodar(config) == executar.SUCESSO
    assert consultar(config, "SELECT count(*) FROM vagas")[0][0] == 20
    assert consultar(config, "SELECT count(*) FROM eventos")[0][0] == 8
    resumo = consultar(config, "SELECT resumo FROM execucoes ORDER BY id")[1][0]
    assert "0 novas, 0 atualizadas, 20 iguais" in resumo


def test_o_dia_seguinte_traz_novas_atualizadas_e_inativas(config, mudar_dia):
    rodar(config)
    mudar_dia(2)
    rodar(config)
    resumo = consultar(config, "SELECT resumo FROM execucoes ORDER BY id")[1][0]
    assert "3 novas, 2 atualizadas, 17 iguais, 1 inativadas" in resumo
    inativas = consultar(config, "SELECT id_externo FROM vagas WHERE ativa=0")
    assert inativas == [("v015",)]
    salario = consultar(
        config, "SELECT salario_min, salario_max FROM vagas "
        "WHERE id_externo='v003'")
    assert salario == [(1500000, 1900000)]


def test_dados_limpos_no_banco(config):
    rodar(config)
    linha = consultar(
        config, "SELECT cidade, uf, modalidade, salario_min, salario_max, tags "
        "FROM vagas WHERE id_externo='v002'")[0]
    assert linha == (None, None, "Remoto", 700000, 950000,
                     "python,pandas,sql,power bi")
    evento = consultar(
        config, "SELECT inicio, online, preco_centavos, preco_estudante_centavos"
        " FROM eventos WHERE id_externo='e004'")[0]
    assert evento == ("2026-11-06T08:30", 0, 12000, 6000)


def test_descricao_vem_da_pagina_de_detalhe(config):
    rodar(config)
    descricao = consultar(
        config, "SELECT descricao FROM vagas WHERE id_externo='v001'")[0][0]
    assert descricao.startswith("A Orbita Software procura")


def test_so_vagas_nao_toca_nos_eventos(config):
    rodar(config, fontes=("vagas",))
    assert consultar(config, "SELECT count(*) FROM eventos")[0][0] == 0


def test_execucao_fica_registrada(config):
    rodar(config)
    linha = consultar(config, "SELECT status, fim IS NOT NULL FROM execucoes")[0]
    assert linha == ("ok", 1)


def test_falha_no_detalhe_gera_resultado_parcial_mas_guarda_a_vaga(config):
    class ClienteQueFalha(Cliente):
        def obter(self, url, params=None):
            if url.endswith("/vagas/v001"):
                raise ErroDeColeta("falha simulada")
            return super().obter(url, params)

    assert rodar(config, cliente=ClienteQueFalha(config)) == executar.PARCIAL
    linha = consultar(
        config, "SELECT titulo, descricao FROM vagas WHERE id_externo='v001'")
    assert linha == [("Desenvolvedor(a) Python Júnior", None)]
    assert consultar(config, "SELECT status FROM execucoes")[0][0] == "parcial"


def test_pagina_de_lista_que_falha_nao_inativa_ninguem(config, mudar_dia):
    rodar(config)

    class ClienteQueFalha(Cliente):
        def obter(self, url, params=None):
            if "pagina=2" in url:
                raise ErroDeColeta("falha simulada")
            return super().obter(url, params)

    mudar_dia(2)
    assert rodar(config, fontes=("vagas",),
                 cliente=ClienteQueFalha(config)) == executar.PARCIAL
    assert consultar(config, "SELECT count(*) FROM vagas WHERE ativa=0")[0][0] == 0


def test_site_fora_do_ar_devolve_falha(config):
    from dataclasses import replace
    assert rodar(replace(config, base_url="http://127.0.0.1:9")) == executar.FALHA
    assert consultar(config, "SELECT status FROM execucoes")[0][0] == "falha"


def test_main_recusa_duas_execucoes_ao_mesmo_tempo(config, tmp_path):
    trava = executar.Trava(config.banco + ".lock")
    assert trava.adquirir()
    codigo = executar.main(["--banco", config.banco, "--base-url", config.base_url,
                            "--pasta-logs", str(tmp_path / "logs"),
                            "--espera", "0"])
    assert codigo == executar.JA_EM_EXECUCAO
    trava.liberar()


def test_main_roda_e_libera_a_trava(config, tmp_path):
    codigo = executar.main(["--banco", config.banco, "--base-url", config.base_url,
                            "--pasta-logs", str(tmp_path / "logs"),
                            "--espera", "0", "--so", "eventos"])
    assert codigo == executar.SUCESSO
    assert not os.path.exists(config.banco + ".lock")
    assert (tmp_path / "logs" / "coleta.log").exists()


def test_trava_abandonada_e_removida(tmp_path):
    caminho = tmp_path / "x.lock"
    caminho.write_text("999")
    antigo = caminho.stat().st_mtime - 10 * 3600
    os.utime(caminho, (antigo, antigo))
    assert executar.Trava(str(caminho), validade_horas=6).adquirir()


# ------------------------------------------- o que NAO pode acontecer no banco
from falsos import CARTAO, ClienteDePaginas, pagina  # noqa: E402


def test_coleta_incompleta_por_vaga_quebrada_nao_inativa_ninguem(config):
    rodar(config, fontes=("vagas",))
    quebrada = ClienteDePaginas(pagina(CARTAO.format(i="x2", titulo="")))
    assert rodar(config, fontes=("vagas",), cliente=quebrada) == executar.PARCIAL
    assert consultar(config, "SELECT count(*) FROM vagas WHERE ativa=0")[0][0] == 0


def test_coleta_com_paginacao_em_ciclo_nao_inativa_ninguem(config):
    rodar(config, fontes=("vagas",))
    ciclo = ClienteDePaginas(pagina(CARTAO.format(i="x1", titulo="T"),
                                proxima="/vagas/"))
    assert rodar(config, fontes=("vagas",), cliente=ciclo) == executar.PARCIAL
    assert consultar(config, "SELECT count(*) FROM vagas WHERE ativa=0")[0][0] == 0


def test_falha_no_detalhe_preserva_a_descricao_ja_conhecida(config):
    rodar(config, fontes=("vagas",))
    antes = consultar(
        config, "SELECT descricao FROM vagas WHERE id_externo='v001'")[0][0]

    class ClienteQueFalha(Cliente):
        def obter(self, url, params=None):
            if url.endswith("/vagas/v001"):
                raise ErroDeColeta("503 simulado")
            return super().obter(url, params)

    assert rodar(config, fontes=("vagas",),
                 cliente=ClienteQueFalha(config)) == executar.PARCIAL
    depois = consultar(
        config, "SELECT descricao FROM vagas WHERE id_externo='v001'")[0][0]
    assert antes and depois == antes
    resumo = consultar(config, "SELECT resumo FROM execucoes ORDER BY id")[1][0]
    assert "0 novas, 0 atualizadas, 20 iguais" in resumo
