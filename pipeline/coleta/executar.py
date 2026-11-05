"""O pipeline de ponta a ponta: coletar, limpar, gravar e registrar."""
import argparse
import logging
import os
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from coleta import banco, coletores
from coleta.config import Config
from coleta.http import BloqueadoPorRobots, Cliente, RobotsIndisponivel

log = logging.getLogger("coleta")

SUCESSO, PARCIAL, FALHA, JA_EM_EXECUCAO = 0, 1, 2, 3


class Trava:
    """Impede duas execuções ao mesmo tempo, com um arquivo de trava."""

    def __init__(self, caminho: str, validade_horas: float = 6.0):
        self.caminho = caminho
        self.validade = validade_horas * 3600

    def adquirir(self) -> bool:
        Path(self.caminho).parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                idade = time.time() - os.path.getmtime(self.caminho)
                if idade < self.validade:
                    return False
                log.warning("trava abandonada há %.1f h: removendo", idade / 3600)
                os.remove(self.caminho)
                continue
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        return False

    def liberar(self) -> None:
        if os.path.exists(self.caminho):
            os.remove(self.caminho)


def configurar_logging(pasta: str, detalhado: bool = False) -> None:
    Path(pasta).mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    raiz = logging.getLogger("coleta")
    raiz.handlers.clear()
    raiz.setLevel(logging.DEBUG if detalhado else logging.INFO)
    arquivo = RotatingFileHandler(Path(pasta) / "coleta.log",
                                  maxBytes=1_000_000, backupCount=3,
                                  encoding="utf-8")
    console = logging.StreamHandler()
    for destino in (arquivo, console):
        destino.setFormatter(formato)
        raiz.addHandler(destino)


def agora() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def ler_argumentos(argv=None) -> argparse.Namespace:
    padrao = Config()
    ap = argparse.ArgumentParser(
        prog="python -m coleta",
        description="Coleta vagas e eventos do Mural Tech")
    ap.add_argument("--base-url", default=padrao.base_url)
    ap.add_argument("--banco", default=padrao.banco)
    ap.add_argument("--pasta-logs", default=padrao.pasta_logs)
    ap.add_argument("--espera", type=float, default=None,
                    help="segundos entre pedidos (padrão: o Crawl-delay do site)")
    ap.add_argument("--max-paginas", type=int, default=padrao.max_paginas)
    ap.add_argument("--so", choices=["vagas", "eventos"], default=None)
    ap.add_argument("-v", "--detalhado", action="store_true")
    return ap.parse_args(argv)


def executar(config: Config, fontes: tuple[str, ...], cliente=None) -> int:
    conn = banco.abrir(config.banco)
    inicio = agora()
    id_execucao = banco.iniciar_execucao(conn, inicio)
    resumos, erros_total, status = [], 0, "ok"
    try:
        cliente = cliente or Cliente(config)
        cliente.carregar_robots()
        etapas = {"vagas": ("vagas", coletores.coletar_vagas),
                  "eventos": ("eventos", coletores.coletar_eventos)}
        for fonte in fontes:
            tabela, coletar = etapas[fonte]
            resultado = coletar(cliente, config)
            with conn:
                contagem = banco.gravar(conn, tabela, resultado.itens, inicio)
                if resultado.completo:
                    contagem.inativadas = banco.inativar_nao_vistas(
                        conn, tabela, coletores.FONTE, inicio)
            erros_total += len(resultado.erros)
            resumos.append(f"{fonte}: {contagem}")
            log.info("%s: %s", fonte, contagem)
            for erro in resultado.erros:
                log.warning("%s: %s", fonte, erro)
        if erros_total:
            status = "parcial"
    except (RobotsIndisponivel, BloqueadoPorRobots) as erro:
        log.error("coleta interrompida: %s", erro)
        status = "falha"
        resumos.append(str(erro))
    except Exception as erro:               # qualquer surpresa vira "falha"
        log.exception("erro inesperado")
        status = "falha"
        resumos.append(f"{type(erro).__name__}: {erro}")
    banco.finalizar_execucao(conn, id_execucao, agora(), status,
                             " | ".join(resumos))
    conn.close()
    log.info("execução %d terminou: %s (%d pedidos, %d repetições)", id_execucao,
             status, getattr(cliente, "pedidos", 0),
             getattr(cliente, "repeticoes", 0))
    return {"ok": SUCESSO, "parcial": PARCIAL, "falha": FALHA}[status]


def main(argv=None) -> int:
    args = ler_argumentos(argv)
    config = Config(base_url=args.base_url, banco=args.banco,
                    pasta_logs=args.pasta_logs, espera=args.espera,
                    max_paginas=args.max_paginas)
    configurar_logging(config.pasta_logs, args.detalhado)
    trava = Trava(config.banco + ".lock")
    if not trava.adquirir():
        log.error("outra execução está em andamento: saindo")
        return JA_EM_EXECUCAO
    try:
        fontes = (args.so,) if args.so else ("vagas", "eventos")
        return executar(config, fontes)
    finally:
        trava.liberar()
