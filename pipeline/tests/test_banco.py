import sqlite3

import pytest

from coleta import banco
from coleta.modelos import Vaga


def vaga(id_externo="v1", titulo="Dev Python", salario_max=500000):
    return Vaga(fonte="teste", id_externo=id_externo, titulo=titulo,
                url=f"http://s/{id_externo}", salario_max=salario_max,
                tags=["python"])


@pytest.fixture
def conn():
    return banco.abrir(":memory:")


def total(conn, tabela="vagas"):
    return conn.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]


def test_primeira_gravacao_cria(conn):
    contagem = banco.gravar(conn, "vagas", [vaga("a"), vaga("b")], "t1")
    assert (contagem.novas, contagem.iguais, contagem.atualizadas) == (2, 0, 0)
    assert total(conn) == 2


def test_gravar_de_novo_nao_duplica(conn):
    banco.gravar(conn, "vagas", [vaga("a")], "t1")
    contagem = banco.gravar(conn, "vagas", [vaga("a")], "t2")
    assert (contagem.novas, contagem.iguais) == (0, 1)
    assert total(conn) == 1


def test_mudanca_atualiza_a_mesma_linha(conn):
    banco.gravar(conn, "vagas", [vaga("a", salario_max=500000)], "t1")
    contagem = banco.gravar(conn, "vagas", [vaga("a", salario_max=600000)], "t2")
    linha = conn.execute("SELECT * FROM vagas").fetchone()
    assert contagem.atualizadas == 1 and total(conn) == 1
    assert linha["salario_max"] == 600000
    assert (linha["primeira_vez"], linha["visto_em"]) == ("t1", "t2")


def test_quem_nao_apareceu_e_inativado_e_volta_a_ativar(conn):
    banco.gravar(conn, "vagas", [vaga("a"), vaga("b")], "t1")
    banco.gravar(conn, "vagas", [vaga("a")], "t2")
    assert banco.inativar_nao_vistas(conn, "vagas", "teste", "t2") == 1
    ativa_b = conn.execute("SELECT ativa FROM vagas WHERE id_externo='b'")
    assert ativa_b.fetchone()[0] == 0
    banco.gravar(conn, "vagas", [vaga("a"), vaga("b")], "t3")
    ativa_b = conn.execute("SELECT ativa FROM vagas WHERE id_externo='b'")
    assert ativa_b.fetchone()[0] == 1


def test_o_banco_recusa_duplicata_mesmo_sem_o_codigo(conn):
    banco.gravar(conn, "vagas", [vaga("a")], "t1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO vagas (fonte, id_externo, titulo, url, conteudo_hash,"
            " primeira_vez, visto_em) VALUES ('teste','a','x','u','h','t','t')")


def test_o_banco_recusa_titulo_vazio(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO vagas (fonte, id_externo, titulo, url, conteudo_hash,"
            " primeira_vez, visto_em) VALUES ('t','z',NULL,'u','h','t','t')")


def test_parametros_protegem_de_sql_injection(conn):
    malicioso = "x'; DROP TABLE vagas; --"
    banco.gravar(conn, "vagas", [vaga("a", titulo=malicioso)], "t1")
    assert total(conn) == 1
    assert conn.execute("SELECT titulo FROM vagas").fetchone()[0] == malicioso
