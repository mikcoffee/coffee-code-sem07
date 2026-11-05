"""O banco: esquema, gravação sem duplicar e o histórico das execuções."""
import sqlite3
from dataclasses import dataclass
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte         TEXT NOT NULL,
    id_externo    TEXT NOT NULL,
    titulo        TEXT NOT NULL,
    empresa       TEXT,
    cidade        TEXT,
    uf            TEXT,
    modalidade    TEXT,
    nivel         TEXT,
    salario_min   INTEGER,
    salario_max   INTEGER,
    publicada     TEXT,
    tags          TEXT,
    url           TEXT NOT NULL,
    descricao     TEXT,
    conteudo_hash TEXT NOT NULL,
    ativa         INTEGER NOT NULL DEFAULT 1,
    primeira_vez  TEXT NOT NULL,
    visto_em      TEXT NOT NULL,
    UNIQUE (fonte, id_externo)
);
CREATE TABLE IF NOT EXISTS eventos (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte                    TEXT NOT NULL,
    id_externo               TEXT NOT NULL,
    titulo                   TEXT NOT NULL,
    inicio                   TEXT,
    local                    TEXT,
    online                   INTEGER NOT NULL DEFAULT 0,
    preco_centavos           INTEGER,
    preco_estudante_centavos INTEGER,
    organizacao              TEXT,
    url                      TEXT NOT NULL,
    conteudo_hash            TEXT NOT NULL,
    ativa                    INTEGER NOT NULL DEFAULT 1,
    primeira_vez             TEXT NOT NULL,
    visto_em                 TEXT NOT NULL,
    UNIQUE (fonte, id_externo)
);
CREATE TABLE IF NOT EXISTS execucoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio    TEXT NOT NULL,
    fim       TEXT,
    status    TEXT NOT NULL,
    resumo    TEXT,
    mensagem  TEXT
);
"""


@dataclass
class Contagem:
    novas: int = 0
    atualizadas: int = 0
    iguais: int = 0
    inativadas: int = 0

    def __str__(self) -> str:
        return (f"{self.novas} novas, {self.atualizadas} atualizadas, "
                f"{self.iguais} iguais, {self.inativadas} inativadas")


def abrir(caminho: str) -> sqlite3.Connection:
    if caminho != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.executescript(ESQUEMA)
    return conn


def gravar(conn, tabela: str, itens: list, agora: str) -> Contagem:
    """Grava os itens sem duplicar. O nome da tabela é nosso, nunca do usuário."""
    contagem = Contagem()
    for item in itens:
        existente = conn.execute(
            f"SELECT * FROM {tabela} WHERE fonte = ? AND id_externo = ?",
            (item.fonte, item.id_externo),
        ).fetchone()
        for campo in getattr(item, "indisponiveis", ()):
            if existente is not None:   # não deu para ler hoje: mantém o antigo
                setattr(item, campo, existente[campo])
        linha = item.como_linha()
        hash_novo = item.conteudo_hash()
        if existente and existente["conteudo_hash"] == hash_novo:
            conn.execute(
                f"UPDATE {tabela} SET visto_em = ?, ativa = 1 "
                "WHERE fonte = ? AND id_externo = ?",
                (agora, item.fonte, item.id_externo),
            )
            contagem.iguais += 1
            continue
        colunas = ["fonte", "id_externo", *linha, "conteudo_hash",
                   "primeira_vez", "visto_em"]
        valores = [item.fonte, item.id_externo, *linha.values(), hash_novo,
                   agora, agora]
        atualizar = ", ".join(f"{c} = excluded.{c}" for c in
                              [*linha, "conteudo_hash", "visto_em"])
        conn.execute(
            f"INSERT INTO {tabela} ({', '.join(colunas)}) "
            f"VALUES ({', '.join('?' * len(colunas))}) "
            "ON CONFLICT (fonte, id_externo) "
            f"DO UPDATE SET {atualizar}, ativa = 1",
            valores,
        )
        if existente:
            contagem.atualizadas += 1
        else:
            contagem.novas += 1
    return contagem


def inativar_nao_vistas(conn, tabela: str, fonte: str, agora: str) -> int:
    """Marca como inativos os itens que não apareceram na coleta de agora."""
    cursor = conn.execute(
        f"UPDATE {tabela} SET ativa = 0 "
        "WHERE fonte = ? AND ativa = 1 AND visto_em < ?",
        (fonte, agora),
    )
    return cursor.rowcount


def iniciar_execucao(conn, inicio: str) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO execucoes (inicio, status) VALUES (?, 'rodando')",
            (inicio,),
        )
    return cursor.lastrowid


def finalizar_execucao(conn, id_execucao: int, fim: str, status: str,
                       resumo: str, mensagem: str = "") -> None:
    with conn:
        conn.execute(
            "UPDATE execucoes SET fim = ?, status = ?, resumo = ?, "
            "mensagem = ? WHERE id = ?",
            (fim, status, resumo, mensagem, id_execucao),
        )
