import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse
import os
import re
import time
import logging

# Configurazione del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configurazione del Crawler ---
START_URL = "https://studenticattolica.unicatt.it/"
ALLOWED_DOMAIN = urlparse(START_URL).netloc
MAX_DEPTH = 10
OUTPUT_DIR = "output_markdown"
REQUEST_DELAY = 1  # Secondi di attesa tra le richieste per essere gentili con il server
USER_AGENT = "MySimplePythonCrawler/1.0 (+http://example.com/botinfo)" # Cambia con info reali se necessario
# ----------------------------------

def sanitize_filename(url_path):
    """Crea un nome file sicuro da un percorso URL."""
    if not url_path or url_path == "/":
        filename = "index"
    else:
        # Rimuovi lo schema e il netloc se presenti per errore (dovrebbe essere solo il path)
        parsed_url = urlparse(url_path)
        path = parsed_url.path
        
        # Rimuovi slash iniziali/finali
        filename = path.strip('/')
        # Sostituisci slash con underscore
        filename = filename.replace('/', '_')
        # Rimuovi caratteri non alfanumerici o non underscore/punto/trattino
        filename = re.sub(r'[^\w_.-]', '', filename)
        # Rimuovi estensioni comuni come .html, .php, .asp se presenti alla fine
        filename = re.sub(r'\.(html|php|asp|aspx)$', '', filename, flags=re.IGNORECASE)
        if not filename: # Se dopo la pulizia è vuoto
            filename = "page_" + str(hash(url_path))[:8] # fallback

    return f"{filename}.md"

def fetch_page(url):
    """Scarica il contenuto di una pagina web."""
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Solleva un'eccezione per codici di errore HTTP (4xx o 5xx)
        # Assicurati che il contenuto sia testo/html prima di procedere
        if 'text/html' in response.headers.get('Content-Type', '').lower():
            return response.text
        else:
            logging.warning(f"Contenuto non HTML per {url}: {response.headers.get('Content-Type')}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Errore durante il fetch di {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Errore generico durante il fetch di {url}: {e}")
        return None


def parse_and_save(html_content, url, current_depth):
    """
    Analizza il contenuto HTML, salva in Markdown e restituisce i link trovati.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Estrazione del contenuto principale (da personalizzare se necessario) ---
    # Prova con tag comuni per il contenuto principale
    main_content_tags = ['main', 'article', 'div[class*="content"]', 'div[id*="content"]']
    content_element = None
    for tag_selector in main_content_tags:
        content_element = soup.select_one(tag_selector)
        if content_element:
            break
    
    if not content_element: # Fallback al body se non trova un main specifico
        content_element = soup.body
    
    if not content_element:
        logging.warning(f"Nessun elemento <body> trovato in {url}")
        return []
        
    html_to_convert = str(content_element)
    # ---------------------------------------------------------------------------

    try:
        markdown_content = md(html_to_convert, heading_style='atx')
    except Exception as e:
        logging.error(f"Errore durante la conversione in Markdown per {url}: {e}")
        markdown_content = f"# Errore durante la conversione\n\nURL: {url}\nErrore: {e}"

    filename = sanitize_filename(urlparse(url).path)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Pagina: {url}\n\n")
            f.write(f"## Profondità: {current_depth}\n\n")
            f.write(markdown_content)
        logging.info(f"Salvato: {filepath} (Profondità: {current_depth})")
    except IOError as e:
        logging.error(f"Errore durante il salvataggio di {filepath}: {e}")
        return [] # Non continuare se non si può salvare

    # Estrazione dei link
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Costruisci URL assoluto
        absolute_url = urljoin(url, href)
        # Rimuovi frammenti (#section) e parametri opzionali se non necessari
        absolute_url = urlparse(absolute_url)._replace(query='', fragment='').geturl()
        links.append(absolute_url)
    
    return links

def crawl():
    """Funzione principale del crawler."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logging.info(f"Cartella di output creata: {OUTPUT_DIR}")

    queue = [(START_URL, 0)]  # (url, depth)
    visited_urls = set()
    pages_crawled_count = 0

    while queue:
        current_url, current_depth = queue.pop(0)

        if current_url in visited_urls:
            logging.debug(f"Già visitato: {current_url}")
            continue

        if current_depth > MAX_DEPTH:
            logging.info(f"Profondità massima raggiunta per il ramo di {current_url}")
            continue
        
        parsed_url = urlparse(current_url)
        if parsed_url.netloc != ALLOWED_DOMAIN:
            logging.debug(f"Dominio non consentito: {current_url}")
            continue

        logging.info(f"Crawling: {current_url} (Profondità: {current_depth})")
        visited_urls.add(current_url)
        
        html_content = fetch_page(current_url)
        
        if html_content:
            pages_crawled_count += 1
            new_links = parse_and_save(html_content, current_url, current_depth)
            
            for link in new_links:
                if link not in visited_urls and urlparse(link).netloc == ALLOWED_DOMAIN:
                    queue.append((link, current_depth + 1))
        
        # Sii gentile con il server
        time.sleep(REQUEST_DELAY)

    logging.info(f"Crawling completato. Pagine totali analizzate: {pages_crawled_count}")
    logging.info(f"Pagine uniche visitate (o tentate): {len(visited_urls)}")

if __name__ == "__main__":
    crawl()