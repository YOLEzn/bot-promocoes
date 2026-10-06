import html
import os
import time

import requests
from bs4 import BeautifulSoup

# O token NÃO fica mais no código. Defina antes de rodar:
#   export TELEGRAM_TOKEN="seu_token_novo"
#   export CHAT_ID="-100..."
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TAG_AFILIADO = os.environ.get("TAG_AFILIADO", "jo5395943")

ARQUIVO_HISTORICO = "enviados.txt"
URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas"
MAX_OFERTAS = 10
INTERVALO = 90 * 60  # 90 minutos

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def carregar_historico():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return set()
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return {linha.strip() for linha in f if linha.strip()}


def salvar_no_historico(link):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def limpar_link(href):
    # tira query string e fragmento (#polycard...), senão o mesmo produto
    # aparece com links diferentes e fura o histórico
    return href.split("?")[0].split("#")[0]


def pegar_foto(card):
    img = card.select_one("img")
    if not img:
        return None
    for attr in ("data-src", "src", "data-srcset"):
        valor = img.get(attr)
        if valor and valor.startswith("http"):
            return valor.split(" ")[0]
    return None


def pegar_preco(card):
    # o ML mostra o preço antigo riscado primeiro, então pego o último
    # valor da lista. Vale conferir no HTML real se isso continua valendo.
    fracoes = card.select(".andes-money-amount__fraction")
    if not fracoes:
        return "Confira no site"
    return f"R$ {fracoes[-1].get_text(strip=True)}"


def obter_ofertas():
    print("Buscando ofertas no Mercado Livre...")
    try:
        resp = requests.get(URL_OFERTAS, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Erro ao acessar o ML: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    historico = carregar_historico()
    vistos = set()  # evita repetir o mesmo produto dentro do mesmo ciclo
    ofertas = []

    cards = soup.select("li.promotion-item, .promotions_element, .poly-card")

    for card in cards:
        if len(ofertas) >= MAX_OFERTAS:
            break

        titulo_el = card.select_one(
            ".promotion-item__title, .promotions_element__title, "
            ".poly-component__title, h3"
        )
        link_el = card.select_one("a[href]")
        if not titulo_el or not link_el:
            continue

        link_base = limpar_link(link_el["href"])
        if link_base in historico or link_base in vistos:
            continue
        vistos.add(link_base)

        ofertas.append({
            "titulo": " ".join(titulo_el.get_text().split()),
            "preco": pegar_preco(card),
            "link_base": link_base,
            "link": f"{link_base}?matt_tool={TAG_AFILIADO}",
            "foto": pegar_foto(card),
        })

    print(f"{len(ofertas)} ofertas novas")
    return ofertas


def montar_legenda(produto):
    # escapa o título, senão um "&" ou "<" quebra o parse_mode HTML
    titulo = html.escape(produto["titulo"])
    link = html.escape(produto["link"], quote=True)
    return (
        f"🔥 <b>{titulo}</b>\n\n"
        f"💰 <b>{produto['preco']}</b>\n"
        f"<i>Preço pode mudar a qualquer momento.</i>\n\n"
        f"🛒 <a href=\"{link}\">Ver no Mercado Livre</a>"
    )[:1024]  # limite de legenda do Telegram em foto


def enviar_telegram(produto):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    legenda = montar_legenda(produto)

    if produto["foto"]:
        url = f"{base}/sendPhoto"
        dados = {"chat_id": CHAT_ID, "photo": produto["foto"],
                 "caption": legenda, "parse_mode": "HTML"}
    else:
        url = f"{base}/sendMessage"
        dados = {"chat_id": CHAT_ID, "text": legenda, "parse_mode": "HTML"}

    try:
        res = requests.post(url, data=dados, timeout=10)
    except requests.RequestException as e:
        print(f"Falha de rede: {e}")
        return

    if res.status_code == 200:
        print(f"Enviado: {produto['titulo']}")
        salvar_no_historico(produto["link_base"])
    elif res.status_code == 429:
        # Telegram mandou segurar; espera o tempo que ele pedir
        espera = res.json().get("parameters", {}).get("retry_after", 30)
        print(f"Limite do Telegram, aguardando {espera}s")
        time.sleep(espera)
    else:
        print(f"Erro {res.status_code}: {res.text}")


def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise SystemExit("Defina TELEGRAM_TOKEN e CHAT_ID.")

    uma_vez = os.environ.get("EXECUTAR_UMA_VEZ") == "1"

    while True:
        try:
            for produto in obter_ofertas():
                enviar_telegram(produto)
                time.sleep(3)
        except Exception as e:
            print(f"Erro no ciclo: {e}")

        if uma_vez:
            break  # no Actions, termina aqui
        print(f"Próxima checagem em {INTERVALO // 60} min")
        time.sleep(INTERVALO)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot encerrado.")
