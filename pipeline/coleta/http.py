"""O cliente HTTP educado: robots.txt, espera entre pedidos e tentativas."""
import logging
import random
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests

from coleta.config import Config

log = logging.getLogger("coleta.http")

STATUS_REPETIVEIS = {429, 502, 503, 504}


class ErroDeColeta(Exception):
    """Uma página não pôde ser baixada, mesmo depois das tentativas."""


class BloqueadoPorRobots(ErroDeColeta):
    """O robots.txt do site pede que esta página não seja coletada."""


class RobotsIndisponivel(ErroDeColeta):
    """Não foi possível ler o robots.txt: por segurança, não coletamos."""


class Cliente:
    def __init__(self, config: Config, dormir=time.sleep):
        self.config = config
        self.dormir = dormir
        self.sessao = requests.Session()
        self.sessao.headers["User-Agent"] = config.user_agent
        self.robots = RobotFileParser()
        self.espera = config.espera or 0.0
        self.pedidos = 0
        self.repeticoes = 0
        self._ultimo = 0.0

    # ---------------------------------------------------------- robots.txt
    def carregar_robots(self) -> None:
        url = urljoin(self.config.base_url, "/robots.txt")
        try:
            resposta = self.sessao.get(url, timeout=self.config.timeout)
        except requests.RequestException as erro:
            raise RobotsIndisponivel(f"robots.txt inacessível: {erro}") from erro
        if resposta.status_code >= 500:
            raise RobotsIndisponivel(f"robots.txt: HTTP {resposta.status_code}")
        if resposta.status_code >= 400:
            self.robots.parse([])      # não existe: nada foi proibido
            log.info("robots.txt ausente (HTTP %s)", resposta.status_code)
        else:
            self.robots.parse(resposta.text.splitlines())
        pedido = self.robots.crawl_delay(self.config.user_agent)
        if self.config.espera is None:
            self.espera = float(pedido) if pedido else 0.0
        log.info("robots.txt lido; espera entre pedidos: %.2fs", self.espera)

    def pode(self, url: str) -> bool:
        return self.robots.can_fetch(self.config.user_agent, url)

    # ---------------------------------------------------------- pedidos
    def obter(self, url: str, params: dict | None = None) -> requests.Response:
        if not self.pode(url):
            raise BloqueadoPorRobots(f"o robots.txt não permite: {url}")
        motivo = "sem resposta"
        total = self.config.max_tentativas
        for tentativa in range(1, total + 1):
            self._respeitar_espera()
            retry_after = None
            try:
                resposta = self.sessao.get(
                    url, params=params, timeout=self.config.timeout
                )
            except (requests.Timeout, requests.ConnectionError) as erro:
                motivo = type(erro).__name__
            else:
                self.pedidos += 1
                codigo = resposta.status_code
                if codigo not in STATUS_REPETIVEIS:
                    if codigo >= 400:
                        raise ErroDeColeta(f"{url}: HTTP {codigo}")
                    return resposta
                motivo = f"HTTP {codigo}"
                retry_after = resposta.headers.get("Retry-After")
            if tentativa < total:
                espera = self._espera_da_tentativa(tentativa, retry_after)
                self.repeticoes += 1
                log.warning("%s em %s: tentativa %d de %d, esperando %.1fs",
                            motivo, url, tentativa, total, espera)
                self.dormir(espera)
        raise ErroDeColeta(f"{url}: {motivo} depois de {total} tentativas")

    def _respeitar_espera(self) -> None:
        falta = self.espera - (time.monotonic() - self._ultimo)
        if falta > 0 and self._ultimo:
            self.dormir(falta)
        self._ultimo = time.monotonic()

    def _espera_da_tentativa(self, tentativa: int, retry_after) -> float:
        base = min(self.config.espera_maxima,
                   self.config.espera_base * 2 ** (tentativa - 1))
        espera = base + random.uniform(0, base * 0.1)
        try:
            pedido = float(retry_after)
        except (TypeError, ValueError):
            return espera
        return max(espera, min(pedido, self.config.espera_maxima))
