"""Um cliente de mentira, para testar o coletor com páginas sob medida."""

CARTAO = ('<article class="vaga" data-id="{i}"><h2 class="titulo">'
          '<a href="/vagas/{i}">{titulo}</a></h2><p class="empresa">E</p>'
          '</article>')


def pagina(corpo, proxima=None):
    link = f'<a rel="next" href="{proxima}">Próxima</a>' if proxima else ""
    return f"<html><body>{corpo}{link}</body></html>"


class Resposta:
    def __init__(self, html):
        self.content = html.encode("utf-8")


class ClienteDePaginas:
    """A lista é fixa; o detalhe devolve uma descrição, ou levanta o erro dado."""
    pedidos = 0
    repeticoes = 0

    def __init__(self, lista, erro_no_detalhe=None):
        self.lista = lista
        self.erro_no_detalhe = erro_no_detalhe

    def carregar_robots(self):
        pass

    def obter(self, url, params=None):
        if "/vagas/x" in url:
            if self.erro_no_detalhe is not None:
                raise self.erro_no_detalhe
            return Resposta('<div class="descricao"><p>desc</p></div>')
        return Resposta(self.lista)
