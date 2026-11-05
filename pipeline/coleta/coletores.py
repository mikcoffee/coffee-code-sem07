"""Coleta: percorre as páginas de cada fonte e monta os dados limpos."""
import logging
from dataclasses import dataclass, field
from urllib.parse import urljoin

from coleta import limpeza, parsers
from coleta.config import Config
from coleta.http import BloqueadoPorRobots, Cliente, ErroDeColeta
from coleta.modelos import Evento, Vaga

log = logging.getLogger("coleta.coletores")
FONTE = "mural-tech"


@dataclass
class Resultado:
    itens: list = field(default_factory=list)
    erros: list = field(default_factory=list)
    completo: bool = True   # só coleta completa pode marcar itens ausentes


def montar_vaga(bruto: dict, descricao: str | None,
                indisponiveis: tuple[str, ...] = ()) -> Vaga | None:
    titulo = limpeza.limpar_texto(bruto["titulo"])
    if not titulo or not bruto["url"]:
        return None
    cidade, uf = limpeza.parse_local(bruto["local"])
    minimo, maximo = limpeza.parse_faixa_salarial(bruto["salario"])
    return Vaga(
        fonte=FONTE, id_externo=bruto["id_externo"], titulo=titulo,
        url=bruto["url"], empresa=limpeza.limpar_texto(bruto["empresa"]),
        cidade=cidade, uf=uf,
        modalidade=limpeza.limpar_texto(bruto["modalidade"]),
        nivel=limpeza.limpar_texto(bruto["nivel"]),
        salario_min=minimo, salario_max=maximo, publicada=bruto["publicada"],
        tags=[t.lower() for t in bruto["tags"]], descricao=descricao,
        indisponiveis=indisponiveis,
    )


def coletar_vagas(cliente: Cliente, config: Config) -> Resultado:
    resultado = Resultado()
    url = urljoin(config.base_url, "/vagas/")
    visitadas = set()
    for _ in range(config.max_paginas):
        if url in visitadas:            # a paginação voltou a um lugar visto
            resultado.completo = False
            resultado.erros.append("ciclo detectado na paginação")
            break
        visitadas.add(url)
        try:
            sopa = parsers.ler_html(cliente.obter(url))
        except BloqueadoPorRobots:
            raise
        except ErroDeColeta as erro:
            resultado.erros.append(str(erro))
            resultado.completo = False
            break
        for bruto in parsers.ler_vagas_da_pagina(sopa, url):
            descricao, indisponiveis = None, ()
            if bruto["url"] is not None:
                try:
                    detalhe = parsers.ler_html(cliente.obter(bruto["url"]))
                    descricao = parsers.ler_descricao(detalhe)
                except BloqueadoPorRobots:
                    raise
                except ErroDeColeta as erro:
                    resultado.erros.append(str(erro))
                    indisponiveis = ("descricao",)   # não deu para ler hoje
            vaga = montar_vaga(bruto, descricao, indisponiveis)
            if vaga is None:
                resultado.erros.append(f"vaga inválida: {bruto['id_externo']}")
                resultado.completo = False   # existe, mas não deu para reconhecer
            else:
                resultado.itens.append(vaga)
        url = parsers.proxima_pagina(sopa, url)
        if url is None:
            break
    else:
        resultado.completo = False      # acabaram as páginas permitidas
        resultado.erros.append("limite de páginas atingido")
    log.info("vagas: %d coletadas, %d erros", len(resultado.itens),
             len(resultado.erros))
    return resultado


def coletar_eventos(cliente: Cliente, config: Config) -> Resultado:
    resultado = Resultado()
    url = urljoin(config.base_url, "/eventos/")
    try:
        sopa = parsers.ler_html(cliente.obter(url))
    except BloqueadoPorRobots:
        raise
    except ErroDeColeta as erro:
        resultado.erros.append(str(erro))
        resultado.completo = False
        return resultado
    for bruto in parsers.ler_eventos(sopa, url):
        titulo = limpeza.limpar_texto(bruto["titulo"])
        if not titulo or not bruto["url"]:
            resultado.erros.append(f"evento inválido: {bruto['id_externo']}")
            resultado.completo = False  # existe, mas não deu para reconhecer
            continue
        preco, preco_estudante = limpeza.parse_preco(bruto["preco"])
        onde = limpeza.limpar_texto(bruto["onde"])
        inicio = limpeza.parse_data_evento(bruto["quando"])
        if inicio is None:              # guarda o evento, mas avisa
            resultado.erros.append(
                f"evento sem data legível: {bruto['id_externo']}")
        resultado.itens.append(Evento(
            fonte=FONTE, id_externo=bruto["id_externo"], titulo=titulo,
            url=bruto["url"], inicio=inicio,
            local=onde, online=int((onde or "").lower() == "online"),
            preco_centavos=preco, preco_estudante_centavos=preco_estudante,
            organizacao=limpeza.limpar_texto(bruto["organizacao"]),
        ))
    log.info("eventos: %d coletados, %d erros", len(resultado.itens),
             len(resultado.erros))
    return resultado
