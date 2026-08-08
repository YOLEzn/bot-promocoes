import requests
from bs4 import BeautifulSoup

# Configurações do Telegram e Afiliado
TELEGRAM_TOKEN = "8876682124:AAEml_NFulfN9kWX1pK0ZVHzai7L7i157qk"
CHAT_ID = "-1003939333885"
TAG_AFILIADO = "jo5395943"

def obter_ofertas_mercadolivre():
    print("🔍 Buscando ofertas no Mercado Livre...")
    url = "https://www.mercadolivre.com.br/ofertas"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Erro HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ofertas = []
    cards = soup.select("li.promotion-item, .promotions_element, .poly-card, div.andes-card")

    for card in cards[:5]:  # Pega as 5 primeiras ofertas
        try:
            titulo_elem = card.select_one(".promotion-item__title, .promotions_element__title, .poly-component__title, h3")
            if not titulo_elem:
                continue
            titulo = titulo_elem.text.strip()

            link_elem = card.select_one("a")
            if not link_elem or "href" not in link_elem.attrs:
                continue
            link_original = link_elem["href"]

            preco_elem = card.select_one(".andes-money-amount__fraction, .promotion-item__price")
            preco = f"R$ {preco_elem.text.strip()}" if preco_elem else "Confira no site"

            img_elem = card.select_one("img")
            foto_url = None
            if img_elem:
                foto_url = img_elem.get("data-src") or img_elem.get("src")

            link_afiliado = f"{link_original}?matt_tool={TAG_AFILIADO}" if "?" not in link_original else f"{link_original}&matt_tool={TAG_AFILIADO}"

            ofertas.append({
                "titulo": titulo,
                "preco": preco,
                "link": link_afiliado,
                "foto": foto_url
            })
        except Exception:
            continue

    print(f"✅ {len(ofertas)} ofertas encontradas!")
    return ofertas

def enviar_mensagem_telegram(produto):
    caption = (
        f"🚨 <b>OFERTA BOMBÁSTICA!</b> 🚨\n\n"
        f"📦 <b>{produto['titulo']}</b>\n\n"
        f"💥 <b>Por apenas:</b> <code>{produto['preco']}</code>\n"
        f"⚡ <i>Preço sujeito a alteração a qualquer momento!</i>\n\n"
        f"👇 <b>GARANTA O SEU NO LINK ABAIXO:</b>\n"
        f"🛒 <a href='{produto['link']}'>COMPRAR COM DESCONTO</a>"
    )

    if produto["foto"]:
        url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": produto["foto"], "caption": caption, "parse_mode": "HTML"}
    else:
        url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False}

    try:
        res = requests.post(url_api, data=payload, timeout=10)
        if res.status_code == 200:
            print(f"🚀 Enviado: {produto['titulo']}")
        else:
            print(f"⚠️ Erro no envio ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Falha de rede: {e}")

if __name__ == "__main__":
    ofertas = obter_ofertas_mercadolivre()
    for produto in ofertas:
        enviar_mensagem_telegram(produto)
    print("🏁 Processo finalizado.")