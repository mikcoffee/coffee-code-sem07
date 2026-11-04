
"""Mural Tech: um site de treino para praticar coleta de dados (web scraping).

Tudo aqui é FICTÍCIO: empresas, vagas e eventos foram inventados para o estudo.
O servidor roda só no seu computador (127.0.0.1) e usa apenas a biblioteca padrão.

Rodar:   python3 servidor.py
Opções:  --porta 8080   a porta (padrão: 8080)
         --dia 1        qual "dia" de dados mostrar (1 ou 2): o dia 2 tem vagas
                        novas, salários alterados e uma vaga que saiu do ar
         --silencioso   não escrever uma linha de registro por pedido
         --latencia 0.2 atrasar cada resposta (simula um servidor mais lento)
"""
import argparse
import hashlib
import html
import json
import math
import threading
import time
from collections import defaultdict, deque
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

POR_PAGINA = 8
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]

# ---------------------------------------------------------------- dados (fictícios)
# (id, título, empresa, local, modalidade, salário, publicada, nível, tags)
VAGAS_DIA_1 = [
    ("v001", "Desenvolvedor(a) Python Júnior", "Orbita Software", "Curitiba, PR", "Híbrido", "R$ 4.500", "2026-10-08", "Júnior", ["python", "django", "sql"]),
    ("v002", "Analista de Dados Pleno", "Pinhão Dados", "Remoto", "Remoto", "R$ 7.000 a R$ 9.500", "2026-10-08", "Pleno", ["python", "pandas", "sql", "power bi"]),
    ("v003", "Engenheiro(a) de Software Sênior", "Araucária Labs", "Curitiba, PR", "Presencial", "R$ 14.000 a R$ 18.000", "2026-10-07", "Sênior", ["java", "spring", "kubernetes"]),
    ("v004", "Estágio em Desenvolvimento Web", "Cafeteria Digital", "Curitiba, PR", "Presencial", "R$ 1.800", "2026-10-07", "Estágio", ["html", "css", "javascript"]),
    ("v005", "Desenvolvedor(a) Front-end Pleno", "Serra Azul Tech", "Remoto", "Remoto", "R$ 8.000 a R$ 10.000", "2026-10-06", "Pleno", ["react", "typescript"]),
    ("v006", "DevOps Júnior", "Orbita Software", "São José dos Pinhais, PR", "Híbrido", "A combinar", "2026-10-06", "Júnior", ["docker", "linux", "ci"]),
    ("v007", "Analista de QA Pleno", "Pinhão Dados", "Curitiba, PR", "Híbrido", "R$ 5.500 a R$ 7.000", "2026-10-05", "Pleno", ["testes", "selenium", "python"]),
    ("v008", "Cientista de Dados Sênior", "Araucária Labs", "Remoto", "Remoto", "R$ 15.000", "2026-10-05", "Sênior", ["python", "machine learning"]),
    ("v009", "Desenvolvedor(a) Backend Júnior", "Cafeteria Digital", "Remoto", "Remoto", "R$ 4.200 a R$ 5.200", "2026-10-04", "Júnior", ["node", "postgres"]),
    ("v010", "Analista de Suporte N2", "Serra Azul Tech", "Curitiba, PR", "Presencial", "R$ 3.200,50", "2026-10-04", "Pleno", ["suporte", "linux", "redes"]),
    ("v011", "Engenheiro(a) de Dados Pleno", "Orbita Software", "Remoto", "Remoto", "R$ 9.000 a R$ 12.000", "2026-10-03", "Pleno", ["spark", "python", "airflow"]),
    ("v012", "Desenvolvedor(a) Mobile Pleno", "Pinhão Dados", "Curitiba, PR", "Híbrido", "até R$ 11.000", "2026-10-03", "Pleno", ["kotlin", "android"]),
    ("v013", "UX Designer Pleno", "Araucária Labs", "Remoto", "Remoto", "A combinar", "2026-10-02", "Pleno", ["figma", "pesquisa"]),
    ("v014", "Estágio em Ciência de Dados", "Serra Azul Tech", "Curitiba, PR", "Presencial", "R$ 2.000", "2026-10-02", "Estágio", ["python", "estatística"]),
    ("v015", "Analista de Segurança Pleno", "Cafeteria Digital", "Remoto", "Remoto", "R$ 8.500", "2026-10-01", "Pleno", ["segurança", "redes"]),
    ("v016", "Desenvolvedor(a) Go Sênior", "Orbita Software", "Remoto", "Remoto", "R$ 13.000 a R$ 16.000", "2026-10-01", "Sênior", ["go", "microsserviços"]),
    ("v017", "Tech Lead", "Araucária Labs", "Curitiba, PR", "Híbrido", "R$ 17.000", "2026-09-30", "Sênior", ["liderança", "arquitetura"]),
    ("v018", "Analista de BI Júnior", "Pinhão Dados", "Curitiba, PR", "Presencial", "R$ 4.000", "2026-09-30", "Júnior", ["sql", "power bi"]),
    ("v019", "Desenvolvedor(a) PHP Pleno", "Cafeteria Digital", "Remoto", "Remoto", "R$ 6.000 a R$ 8.000", "2026-09-29", "Pleno", ["php", "laravel"]),
    ("v020", "Administrador(a) de Banco de Dados", "Serra Azul Tech", "São José dos Pinhais, PR", "Presencial", "R$ 9.500", "2026-09-29", "Pleno", ["postgres", "mysql"]),
]
VAGAS_NOVAS_DIA_2 = [
    ("v021", "Desenvolvedor(a) Python Pleno", "Orbita Software", "Remoto", "Remoto", "R$ 8.000 a R$ 10.000", "2026-10-09", "Pleno", ["python", "fastapi"]),
    ("v022", "Analista de Dados Júnior", "Pinhão Dados", "Curitiba, PR", "Híbrido", "R$ 4.800", "2026-10-09", "Júnior", ["sql", "python"]),
    ("v023", "Engenheiro(a) de Machine Learning", "Araucária Labs", "Remoto", "Remoto", "R$ 14.000 a R$ 17.000", "2026-10-09", "Sênior", ["python", "pytorch"]),
]
SALARIO_DIA_2 = {"v003": "R$ 15.000 a R$ 19.000", "v007": "R$ 6.000 a R$ 7.500"}
SAIU_NO_DIA_2 = {"v015"}

# (id, título, data ISO, hora, local, preço, organização)
EVENTOS_DIA_1 = [
    ("e001", "Python Day Curitiba", "2026-10-17", "14h00", "Curitiba, PR", "Gratuito", "Comunidade Py Sul"),
    ("e002", "Meetup de Dados", "2026-10-22", "19h30", "Online", "Gratuito", "Pinhão Dados"),
    ("e003", "Workshop de Docker na Prática", "2026-10-24", "09h00", "Curitiba, PR", "R$ 40,00", "Orbita Software"),
    ("e004", "Conferência Web Sul", "2026-11-06", "08h30", "São José dos Pinhais, PR", "R$ 120,00 (estudantes: R$ 60,00)", "Web Sul"),
    ("e005", "Hackathon Cidades Inteligentes", "2026-11-07", "09h00", "Curitiba, PR", "Gratuito", "Araucária Labs"),
    ("e006", "Noite de Código Aberto", "2026-11-11", "19h00", "Online", "Gratuito", "Comunidade Py Sul"),
    ("e007", "Introdução a Machine Learning", "2026-11-14", "10h00", "Online", "R$ 25,00", "Serra Azul Tech"),
    ("e008", "Feira de Carreira em TI", "2026-11-19", "13h00", "Curitiba, PR", "Gratuito", "Cafeteria Digital"),
]
EVENTOS_NOVOS_DIA_2 = [
    ("e009", "Workshop de Coleta Ética de Dados", "2026-12-02", "19h30", "Online", "Gratuito", "Pinhão Dados"),
    ("e010", "Retrospectiva Tech 2026", "2026-12-05", "14h00", "Curitiba, PR", "Gratuito", "Comunidade Py Sul"),
]

ROBOTS = """# Mural Tech (site de treino): regras para robôs
User-agent: *
Allow: /vagas/
Allow: /eventos/
Disallow: /interno/
Crawl-delay: 1

User-agent: BotAbusivo
Disallow: /
"""

ESTADO = {"dia": 1, "latencia": 0.0}
TRAVA = threading.Lock()
CONTADORES_INSTAVEL = defaultdict(int)
JANELA_LIMITE = deque()


def vagas():
    dia = ESTADO["dia"]
    lista = []
    for v in VAGAS_DIA_1 + (VAGAS_NOVAS_DIA_2 if dia == 2 else []):
        if dia == 2 and v[0] in SAIU_NO_DIA_2:
            continue
        if dia == 2 and v[0] in SALARIO_DIA_2:
            v = v[:5] + (SALARIO_DIA_2[v[0]],) + v[6:]
        lista.append(v)
    return sorted(lista, key=lambda v: (v[6], v[0]), reverse=True)


def eventos():
    return sorted(EVENTOS_DIA_1 + (EVENTOS_NOVOS_DIA_2 if ESTADO["dia"] == 2 else []), key=lambda e: e[2])


def data_por_extenso(iso, hora):
    d = date.fromisoformat(iso)
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}, {hora}"


def data_br(iso):
    ano, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{ano}"


# ---------------------------------------------------------------- páginas
def pagina(titulo, corpo, extra_head=""):
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{html.escape(titulo)} | Mural Tech</title>
{extra_head}</head>
<body>
<header><a href="/">Mural Tech</a> <nav><a href="/vagas/">Vagas</a> <a href="/eventos/">Eventos</a></nav></header>
<main>
{corpo}
</main>
<footer><p>Site fictício para estudo de coleta de dados.</p></footer>
</body>
</html>
""".encode("utf-8")


def cartao_vaga(v):
    id_, titulo, empresa, local, modalidade, salario, publicada, nivel, tags = v
    lis = "".join(f"<li>{html.escape(t)}</li>" for t in tags)
    return f"""<article class="vaga" data-id="{id_}">
  <h2 class="titulo"><a href="/vagas/{id_}">{html.escape(titulo)}</a></h2>
  <p class="empresa">{html.escape(empresa)}</p>
  <p class="local">{html.escape(local)}</p>
  <span class="modalidade">{modalidade}</span>
  <span class="nivel">{nivel}</span>
  <span class="salario">{html.escape(salario)}</span>
  <time datetime="{publicada}">{data_br(publicada)}</time>
  <ul class="tags">{lis}</ul>
</article>"""


def pagina_lista_vagas(n):
    todas = vagas()
    total_paginas = max(1, -(-len(todas) // POR_PAGINA))
    n = min(max(n, 1), total_paginas)
    fatia = todas[(n - 1) * POR_PAGINA: n * POR_PAGINA]
    cartoes = "\n".join(cartao_vaga(v) for v in fatia)
    anterior = f'<a rel="prev" href="/vagas/?pagina={n - 1}">Anterior</a>' if n > 1 else ""
    proxima = f'<a rel="next" href="/vagas/?pagina={n + 1}">Próxima</a>' if n < total_paginas else ""
    corpo = f"""<h1>Vagas de tecnologia</h1>
<p class="total">{len(todas)} vagas encontradas</p>
<section class="lista">
{cartoes}
</section>
<nav class="paginacao">{anterior} <span>Página {n} de {total_paginas}</span> {proxima}</nav>"""
    return pagina("Vagas", corpo)


def pagina_detalhe_vaga(id_):
    for v in vagas():
        if v[0] == id_:
            _, titulo, empresa, local, modalidade, salario, publicada, nivel, tags = v
            reqs = "".join(f"<li>Experiência com {html.escape(t)}</li>" for t in tags)
            corpo = f"""<article class="vaga-detalhe" data-id="{id_}">
<h1 class="titulo">{html.escape(titulo)}</h1>
<p class="empresa">{html.escape(empresa)}</p>
<p class="local">{html.escape(local)} ({modalidade})</p>
<p class="salario">{html.escape(salario)}</p>
<time datetime="{publicada}">Publicada em {data_br(publicada)}</time>
<div class="descricao"><p>A {html.escape(empresa)} procura uma pessoa para a posição de {html.escape(titulo)}, nível {nivel}. Você vai trabalhar em um time pequeno, com entregas semanais.</p></div>
<h2>Requisitos</h2>
<ul class="requisitos">{reqs}</ul>
<a class="candidatar" href="/vagas/{id_}#candidatar">Quero me candidatar</a>
</article>"""
            return pagina(titulo, corpo)
    return None


def pagina_eventos():
    itens = "\n".join(f"""<li class="evento" data-id="{e[0]}">
  <h3><a href="/eventos/{e[0]}">{html.escape(e[1])}</a></h3>
  <p class="quando">{data_por_extenso(e[2], e[3])}</p>
  <p class="onde">{html.escape(e[4])}</p>
  <p class="preco">{html.escape(e[5])}</p>
  <p class="organizacao">{html.escape(e[6])}</p>
</li>""" for e in eventos())
    return pagina("Eventos", f'<h1>Eventos de tecnologia</h1>\n<ul class="eventos">\n{itens}\n</ul>')


def pagina_home():
    return pagina("Início", """<h1>Mural Tech</h1>
<p>Vagas e eventos de tecnologia. <a href="/vagas/">Ver vagas</a> | <a href="/eventos/">Ver eventos</a></p>""")


def pagina_quebrada():
    corpo = ("<ul class=\"tags\"><li>Python<li>SQL</ul>\n"
             "<p>um<p>dois <b>negrito <i>itálico</b> fim</i>\n"
             "<p class=resumo>sem aspas no atributo")
    return f"<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><title>Quebrado</title></head><body>{corpo}</body></html>".encode("utf-8")


def pagina_js():
    return pagina("Vagas (carregadas por JavaScript)", """<h1>Vagas de tecnologia</h1>
<div id="resultado">Carregando...</div>
<script>
async function carregar() {
  await new Promise((r) => setTimeout(r, 400));
  const resp = await fetch("/api/vagas?pagina=1&por_pagina=8");
  const dados = await resp.json();
  const alvo = document.getElementById("resultado");
  alvo.replaceChildren();
  for (const v of dados.itens) {
    const art = document.createElement("article");
    art.className = "vaga";
    art.dataset.id = v.id;
    const h = document.createElement("h2"); h.className = "titulo"; h.textContent = v.titulo;
    const e = document.createElement("p"); e.className = "empresa"; e.textContent = v.empresa;
    art.append(h, e);
    alvo.append(art);
  }
}
carregar();
</script>""")


def json_vagas(pagina_n, por_pagina):
    todas = vagas()
    fatia = todas[(pagina_n - 1) * por_pagina: pagina_n * por_pagina]
    itens = [{"id": v[0], "titulo": v[1], "empresa": v[2], "local": v[3], "modalidade": v[4],
              "salario": v[5], "publicada": v[6], "nivel": v[7], "tags": v[8]} for v in fatia]
    return json.dumps({"total": len(todas), "pagina": pagina_n, "por_pagina": por_pagina, "itens": itens}, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------- servidor
class Manipulador(BaseHTTPRequestHandler):
    silencioso = False

    def log_message(self, formato, *args):
        if not Manipulador.silencioso:
            print(f"{self.address_string()} {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)

    def responder(self, codigo, corpo=b"", tipo="text/html; charset=utf-8", extra=None):
        self.send_response(codigo)
        if tipo:
            self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        for chave, valor in (extra or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def responder_com_etag(self, corpo, tipo="text/html; charset=utf-8"):
        etag = '"' + hashlib.md5(corpo).hexdigest()[:16] + '"'
        if self.headers.get("If-None-Match") == etag:
            return self.responder(304, b"", tipo=None, extra={"ETag": etag})
        self.responder(200, corpo, tipo, {"ETag": etag})

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        caminho, q = url.path, parse_qs(url.query)
        if ESTADO["latencia"] and not caminho.startswith("/_dev/"):
            time.sleep(ESTADO["latencia"])   # simula um servidor mais lento
        try:
            if caminho == "/":
                return self.responder(200, pagina_home())
            if caminho == "/robots.txt":
                return self.responder(200, ROBOTS.encode("utf-8"), "text/plain; charset=utf-8")
            if caminho in ("/vagas", "/vagas/"):
                try:
                    n = int(q.get("pagina", ["1"])[0])
                except ValueError:
                    n = 1
                return self.responder_com_etag(pagina_lista_vagas(n))
            if caminho.startswith("/vagas/"):
                corpo = pagina_detalhe_vaga(caminho.rsplit("/", 1)[1])
                return self.responder(200, corpo) if corpo else self.responder(404, pagina("Não encontrada", "<h1>Vaga não encontrada</h1>"))
            if caminho in ("/eventos", "/eventos/"):
                return self.responder_com_etag(pagina_eventos())
            if caminho == "/quebrado/":
                return self.responder(200, pagina_quebrada())
            if caminho == "/legado/vagas":     # sem charset no cabeçalho e sem <meta charset>
                corpo = pagina_lista_vagas(1).replace(b'<meta charset="utf-8">\n', b"")
                return self.responder(200, corpo, tipo="text/html")
            if caminho == "/eco":              # devolve os cabeçalhos que você enviou
                visto = {k.lower(): v for k, v in self.headers.items()}
                return self.responder(200, json.dumps(visto, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            if caminho == "/antigo/vagas":     # redirecionamento permanente
                return self.responder(301, b"", "text/plain", {"Location": "/vagas/"})
            if caminho == "/lento":
                time.sleep(3)
                return self.responder(200, pagina("Lento", "<h1>Demorei, mas cheguei</h1>"))
            if caminho == "/vagas-js/":
                return self.responder(200, pagina_js())
            if caminho == "/api/vagas":
                p = int(q.get("pagina", ["1"])[0]); por = int(q.get("por_pagina", [str(POR_PAGINA)])[0])
                return self.responder(200, json_vagas(p, por), "application/json; charset=utf-8")
            if caminho == "/interno/relatorio":
                return self.responder(200, pagina("Interno", "<h1>Relatório interno</h1><p>O robots.txt pede que robôs não coletem esta área.</p>"))
            if caminho == "/instavel/vagas":     # falha N vezes com 503 e depois responde
                chave = q.get("chave", ["padrao"])[0]; falhas = int(q.get("falhas", ["2"])[0])
                with TRAVA:
                    CONTADORES_INSTAVEL[chave] += 1; vez = CONTADORES_INSTAVEL[chave]
                if vez <= falhas:
                    return self.responder(503, b"Servico indisponivel", "text/plain", {"Retry-After": "1"})
                return self.responder(200, pagina_lista_vagas(1))
            if caminho == "/limitado/vagas":     # no máximo 3 pedidos a cada 5 segundos
                agora = time.monotonic()
                with TRAVA:
                    while JANELA_LIMITE and agora - JANELA_LIMITE[0] > 5:
                        JANELA_LIMITE.popleft()
                    estourou = len(JANELA_LIMITE) >= 3
                    if not estourou:
                        JANELA_LIMITE.append(agora)
                    else:   # quanto falta para o pedido mais antigo sair da janela
                        falta = max(1, math.ceil(5 - (agora - JANELA_LIMITE[0])))
                if estourou:
                    return self.responder(429, b"Muitos pedidos", "text/plain", {"Retry-After": str(falta)})
                return self.responder(200, pagina_lista_vagas(1))
            if caminho.startswith("/_dev/dia/"):   # só para os testes e estudos
                ESTADO["dia"] = 2 if caminho.endswith("2") else 1
                return self.responder(200, f"dia={ESTADO['dia']}".encode(), "text/plain")
            if caminho == "/_dev/latencia":
                ESTADO["latencia"] = float(q.get("valor", ["0"])[0])
                return self.responder(200, f"latencia={ESTADO['latencia']}".encode(), "text/plain")
            if caminho == "/_dev/reset":
                with TRAVA:
                    CONTADORES_INSTAVEL.clear(); JANELA_LIMITE.clear(); ESTADO["dia"] = 1; ESTADO["latencia"] = 0.0
                return self.responder(200, b"ok", "text/plain")
            return self.responder(404, pagina("Não encontrada", "<h1>Página não encontrada</h1>"))
        except (BrokenPipeError, ConnectionResetError):
            pass


def criar_servidor(porta=8080, dia=1, silencioso=True, latencia=0.0):
    ESTADO["dia"] = dia
    ESTADO["latencia"] = latencia
    Manipulador.silencioso = silencioso
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.request_queue_size = 128   # aguenta muitas conexões de uma vez
    return ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mural Tech, o site de treino")
    ap.add_argument("--porta", type=int, default=8080)
    ap.add_argument("--dia", type=int, choices=[1, 2], default=1)
    ap.add_argument("--silencioso", action="store_true")
    ap.add_argument("--latencia", type=float, default=0.0, help="segundos de atraso em cada resposta")
    a = ap.parse_args()
    servidor = criar_servidor(a.porta, a.dia, a.silencioso, a.latencia)
    print(f"Mural Tech no ar em http://127.0.0.1:{a.porta}  (dia {a.dia}). Ctrl+C para parar.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")
