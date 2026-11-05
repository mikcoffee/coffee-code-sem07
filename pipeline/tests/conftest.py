import sys
import threading
from pathlib import Path

import pytest
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / ".." / "site-treino"))

import servidor  # noqa: E402  (o site de treino, usado como servidor de teste)

from coleta.config import Config  # noqa: E402


@pytest.fixture(scope="session")
def site():
    """Liga o Mural Tech em uma porta livre, durante toda a sessão de testes."""
    srv = servidor.criar_servidor(porta=0, dia=1, silencioso=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(autouse=True)
def site_no_estado_inicial(site):
    requests.get(site + "/_dev/reset", timeout=5)


@pytest.fixture
def config(site, tmp_path):
    return Config(base_url=site, banco=str(tmp_path / "vagas.db"),
                  pasta_logs=str(tmp_path / "logs"), espera=0.0,
                  timeout=(2.0, 3.0), espera_base=0.5)


@pytest.fixture
def mudar_dia(site):
    def _mudar(dia):
        requests.get(f"{site}/_dev/dia/{dia}", timeout=5)
    return _mudar
