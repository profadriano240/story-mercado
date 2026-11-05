#!/usr/bin/env python3
"""Gera e publica o Story diário de mercado do @impostodabolsa.

Uso:
  story.py gerar             escreve saida/story.jpg (ou sai sem nada em feriado)
  story.py publicar <url>    publica a imagem da URL pública como Story
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).resolve().parent
SAIDA = RAIZ / "saida" / "story.jpg"
FUSO = ZoneInfo("America/Sao_Paulo")
API_SITE = "https://www.impostodabolsa.com.br/api/cotacoes"
API_DALIAN = "https://hq.sinajs.cn/list=nf_I0"
GRAPH = "https://graph.facebook.com/v27.0"

# Dias sem pregão na B3. Conferir o calendário oficial no fim de cada ano.
FERIADOS_B3 = {
    "2026-11-20", "2026-12-24", "2026-12-25", "2026-12-31",
    "2027-01-01", "2027-02-08", "2027-02-09", "2027-03-26", "2027-04-21",
    "2027-05-27", "2027-09-07", "2027-10-12", "2027-11-02", "2027-11-15",
    "2027-12-24", "2027-12-31",
}


def baixar(url, cabecalhos=None, tentativas=3):
    pedido = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", **(cabecalhos or {})}
    )
    for tentativa in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=20) as resposta:
                return resposta.read()
        except OSError:
            if tentativa == tentativas:
                raise
            time.sleep(5 * tentativa)


def cotacoes_site():
    itens = json.loads(baixar(API_SITE))["itens"]
    por_nome = {item["nome"]: item for item in itens}
    return por_nome["Brent"], por_nome["Dólar"]


def dalian():
    """Devolve último preço, variação sobre o ajuste anterior e data do pregão."""
    bruto = baixar(API_DALIAN, {"Referer": "https://finance.sina.com.cn"})
    texto = bruto.decode("gbk")
    campos = texto.split('"')[1].split(",")
    ultimo, ajuste_anterior = float(campos[8]), float(campos[10])
    if ultimo <= 0 or ajuste_anterior <= 0:
        raise ValueError(f"Dalian sem preço válido: {campos[:18]}")
    variacao = (ultimo / ajuste_anterior - 1) * 100
    return ultimo, variacao, dt.date.fromisoformat(campos[17])


def numero(valor, casas):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor):
    casas = 2 if abs(valor) < 0.1 else 1
    sinal = "+" if valor >= 0 else "−"
    return f"{sinal}{numero(abs(valor), casas)}%"


def movimento(valor):
    """Verbo do título; abaixo de 0,1% trata como estável."""
    if abs(valor) < 0.1:
        return "estável"
    return "sobe" if valor > 0 else "cai"


def titulo(var_brent, var_minerio):
    brent, minerio = movimento(var_brent), movimento(var_minerio)
    if brent == minerio:
        plural = {"sobe": "sobem", "cai": "caem", "estável": "estáveis"}[brent]
        return f"Petróleo e minério {plural} antes da abertura"
    return f"Petróleo {brent} e minério {minerio} antes da abertura".replace(
        "minério estável", "minério fica estável"
    ).replace("Petróleo estável", "Petróleo fica estável")


def linha(nome, unidade, valor, variacao):
    classe = "up" if variacao >= 0 else "dn"
    return (
        f'<div class="l"><div class="n">{nome}<small>{unidade}</small></div>'
        f'<div class="v">{valor}<span class="{classe}">{percentual(variacao)}</span></div></div>'
    )


def montar_html(agora, brent, dolar, minerio):
    preco, var_minerio, pregao = minerio
    unidade = "yuans por tonelada"
    if pregao != agora.date():
        unidade += f" · pregão de {pregao:%d/%m}"
    linhas = "".join([
        linha("Brent", "US$ por barril", numero(brent["preco"], 2), brent["variacao"]),
        linha("Minério em Dalian", unidade, numero(preco, 0), var_minerio),
        linha("Dólar", "R$", numero(dolar["preco"], 2), dolar["variacao"]),
    ])
    modelo = (RAIZ / "story.html").read_text(encoding="utf-8")
    return (
        modelo.replace("{{DATA}}", f"{agora:%d/%m}")
        .replace("{{TITULO}}", titulo(brent["variacao"], var_minerio))
        .replace("{{LINHAS}}", linhas)
        .replace("{{HORA}}", f"{agora.hour}h{agora.minute:02d}")
        .replace("{{LOGO}}", (RAIZ / "logo.svg").as_uri())
    )


def renderizar(html):
    from PIL import Image

    with tempfile.TemporaryDirectory() as pasta:
        pagina = pathlib.Path(pasta) / "story.html"
        png = pathlib.Path(pasta) / "story.png"
        pagina.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                os.environ.get("CHROME", "google-chrome"), "--headless=new",
                "--no-sandbox", "--hide-scrollbars",
                "--allow-file-access-from-files", "--virtual-time-budget=8000",
                "--window-size=1080,1920", f"--screenshot={png}", pagina.as_uri(),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        imagem = Image.open(png).convert("RGB")
        if imagem.size != (1080, 1920):
            raise ValueError(f"Tamanho inesperado: {imagem.size}")
        SAIDA.parent.mkdir(exist_ok=True)
        imagem.save(SAIDA, quality=92)


def gerar():
    agora = dt.datetime.now(FUSO)
    if agora.date().isoformat() in FERIADOS_B3:
        print("Feriado da B3: sem Story hoje.")
        return
    brent, dolar = cotacoes_site()
    minerio = dalian()
    renderizar(montar_html(agora, brent, dolar, minerio))
    print(f"Gerado: Brent {brent['preco']}, Dalian {minerio[0]}, dólar {dolar['preco']}")


def graph(caminho, dados=None):
    token = os.environ["IG_ACCESS_TOKEN"]
    if dados is None:
        separador = "&" if "?" in caminho else "?"
        url, corpo = f"{GRAPH}/{caminho}{separador}access_token={token}", None
    else:
        url = f"{GRAPH}/{caminho}"
        corpo = urllib.parse.urlencode({**dados, "access_token": token}).encode()
    try:
        with urllib.request.urlopen(url if corpo is None else
                                    urllib.request.Request(url, data=corpo),
                                    timeout=60) as resposta:
            return json.load(resposta)
    except urllib.error.HTTPError as erro:
        sys.exit(f"Erro da Meta em {caminho}: {erro.read().decode()[:500]}")


def conta_instagram():
    conta = os.environ.get("IG_USER_ID")
    if conta:
        return conta
    paginas = graph("me/accounts?fields=instagram_business_account")["data"]
    for pagina in paginas:
        if "instagram_business_account" in pagina:
            return pagina["instagram_business_account"]["id"]
    sys.exit("Nenhuma conta do Instagram encontrada para este token.")


def publicar(url):
    conta = conta_instagram()
    container = graph(f"{conta}/media", {"media_type": "STORIES", "image_url": url})["id"]
    for _ in range(12):
        estado = graph(f"{container}?fields=status_code")["status_code"]
        if estado == "FINISHED":
            break
        if estado in ("ERROR", "EXPIRED"):
            sys.exit(f"Meta recusou a mídia: {estado}")
        time.sleep(5)
    else:
        sys.exit("Meta não terminou de processar a mídia em 60 s.")
    print("Publicado:", graph(f"{conta}/media_publish", {"creation_id": container})["id"])


if __name__ == "__main__":
    if sys.argv[1:2] == ["gerar"]:
        gerar()
    elif sys.argv[1:2] == ["publicar"] and len(sys.argv) == 3:
        publicar(sys.argv[2])
    else:
        sys.exit(__doc__)
