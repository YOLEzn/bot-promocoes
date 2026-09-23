import time
import os
import requests
from bs4 import BeautifulSoup

# Configurações do Telegram e Afiliado
TELEGRAM_TOKEN = "8876682124:AAEml_NFulfN9kWX1pK0ZVHzai7L7i157qk"
CHAT_ID = "-1003939333885"
TAG_AFILIADO = "jo5395943"

# Arquivo para armazenar links já enviados e evitar duplicados
ARQUIVO_HISTORICO = "enviados.txt"

def carregar_historico():
    """Carrega o histórico de ofertas já enviadas."""
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def salvar_no_historico(link):
    """Salva um novo link no arquivo de histórico."""
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

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
    historico = carregar_historico()

    cards = soup.select("li.promotion-item, .promotions_element, .poly-card, div.andes-card")

    for card in cards:
        if len(ofertas) >= 10:  # Pára assim que encontrar 10 ofertas novas
            break

        try:
            titulo_elem = card.select_one(".promotion-item__title, .promotions_element__title, .poly-component__title, h3")
            if not titulo_elem:
                continue
            titulo = " ".join(titulo_elem.text.split())

            link_elem = card.select_one("a")
            if not link_elem or "href" not in link_elem.attrs:
                continue
            link_original = link_elem["href"].split("?")[0]  # Limpa parâmetros para comparar com histórico

            # Verifica se esta oferta já foi enviada no passado
            if link_original in historico:
                continue

            preco_elem = card.select_one(".andes-money-amount__fraction, .promotion-item__price")
            preco = f"R$ {preco_elem.text.strip()}" if preco_elem else "Confira no site"

            # === CAPTURA AVANÇADA DE IMAGEM ===
            img_elem = card.select_one("img")
            foto_url = None

            if img_elem:
                atributos_imagem = [
                    img_elem.get("data-src"),
                    img_elem.get("src"),
                    img_elem.get("data-srcset")
                ]
                for src in atributos_imagem:
                    if src and src.startswith("http") and not src.startswith("data:"):
                        foto_url = src.split(" ")[0]
                        break
            # ==================================

            link_afiliado = f"{link_original}?matt_tool={TAG_AFILIADO}"

            ofertas.append({
                "titulo": titulo,
                "preco": preco,
                "link": link_afiliado,
                "link_base": link_original,
                "foto": foto_url
            })
        except Exception:
            continue

    print(f"✅ {len(ofertas)} ofertas novas encontradas!")
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
            # Salva o link no histórico apenas se for enviado com sucesso
            salvar_no_historico(produto["link_base"])
        else:
            print(f"⚠️ Erro no envio ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Falha de rede: {e}")

def executar_bot():
    print("🤖 Bot de ofertas iniciado!")
    
    # Tempo de espera entre cada ciclo (1 hora e 30 minutos = 5400 segundos)
    INTERVALO_SEGUNDOS = 90 * 60  

    while True:
        print("\n--- 🔄 Iniciando novo ciclo de envio ---")
        ofertas = obter_ofertas_mercadolivre()
        
        for produto in ofertas:
            enviar_mensagem_telegram(produto)
            time.sleep(2)  # Pausa curta de 2s entre cada mensagem no Telegram para evitar spam

        print(f"⏳ Aguardando 1 hora e 30 minutos até a próxima verificação...")
        time.sleep(INTERVALO_SEGUNDOS)

if __name__ == "__main__":
    executar_bot()