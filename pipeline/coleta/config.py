"""Configuração do pipeline: um lugar só para os valores que mudam."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    base_url: str = "http://127.0.0.1:8080"
    banco: str = "dados/vagas.db"
    pasta_logs: str = "logs"
    espera: float | None = None    # None: usar o Crawl-delay do robots.txt
    timeout: tuple[float, float] = (3.05, 10.0)    # (conexão, leitura)
    max_tentativas: int = 4
    espera_base: float = 0.5       # backoff: 0,5 s, 1 s, 2 s...
    espera_maxima: float = 30.0    # nunca esperar mais que isso
    max_paginas: int = 20          # trava de segurança da paginação
    user_agent: str = (
        "MuralColetaBot/1.0 (projeto de estudo; contato: voce@example.com)"
    )
