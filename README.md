# StudensBot

Questo progetto consiste in due script Python principali:

1.  **`crawler.py`**: Un web crawler che scarica contenuti dal sito `https://studenticattolica.unicatt.it/`, seguendo i link interni e salvando le pagine come file Markdown.
2.  **`chatbot.py`**: Un chatbot basato su RAG (Retrieval Augmented Generation) che utilizza i file Markdown scaricati dal crawler. Indicizza questi file e permette all'utente di porre domande sul loro contenuto, generando risposte con l'ausilio di un Large Language Model (LLM) come Google Gemini.

## Flusso di Lavoro Generale

1.  **Esegui `crawler.py`**: Questo script popolerà una directory (default: `output_markdown/`) con i file Markdown estratti dal sito.
2.  **Esegui `chatbot.py`**: Questo script:
    *   Leggerà i file Markdown dalla directory specificata.
    *   Creerà (o caricherà) un indice vettoriale del loro contenuto.
    *   Avvierà un'interfaccia a riga di comando per chattare con i documenti, utilizzando Google Gemini per generare le risposte.

## Prerequisiti

Assicurati di avere Python installato (consigliato Python 3.7+).

Le seguenti librerie Python sono necessarie. Puoi installarle tutte insieme:

```bash
pip install requests beautifulsoup4 markdownify langchain langchain-google-genai faiss-cpu python-dotenv unstructured markdown
```

Per crawler.py:
* requests: Per effettuare richieste HTTP.
* beautifulsoup4: Per il parsing dell'HTML.
* markdownify: Per convertire HTML in Markdown.

Per chatbot.py:
* langchain: Framework principale per costruire applicazioni LLM.
* langchain-google-genai: Integrazione Langchain per i modelli Google Gemini.
* faiss-cpu: Per la creazione e la ricerca di indici vettoriali (CPU version).
* python-dotenv: Per caricare variabili d'ambiente (es. API key).

unstructured e markdown: (Consigliate) Dipendenze per UnstructuredMarkdownLoader di Langchain, per un parsing più dettagliato dei file Markdown. In alternativa, lo script può usare TextLoader.

## Configurazione

### Google API Key (per chatbot.py)

Per utilizzare i modelli Gemini tramite Langchain, avrai bisogno di una API key da Google AI Studio:
1. Vai su Google AI Studio.
1. Crea un nuovo progetto o usane uno esistente.
1. Ottieni una API key ("Get API key").
1. Crea un file chiamato .env nella directory principale del progetto (la stessa directory di crawler.py e chatbot.py).
1. Aggiungi la tua API key al file .env in questo formato:

```
GOOGLE_API_KEY="LA_TUA_API_KEY_QUI"
```


### Configurazione degli Script

Entrambi gli script hanno delle variabili di configurazione all'inizio del file che puoi modificare secondo necessità.

```
crawler.py
# --- Configurazione del Crawler ---
START_URL = "https://studenticattolica.unicatt.it/"
ALLOWED_DOMAIN = urlparse(START_URL).netloc
MAX_DEPTH = 10 # Profondità massima di crawling
OUTPUT_DIR = "output_markdown" # Directory per i file .md scaricati
REQUEST_DELAY = 1  # Secondi di attesa tra le richieste
USER_AGENT = "MySimplePythonCrawler/1.0 (+http://example.com/botinfo)"
# ----------------------------------
```
```
chatbot.py
# --- Configurazione ---
MARKDOWN_DIR = "output_markdown"  # DEVE CORRISPONDERE a OUTPUT_DIR del crawler
VECTORSTORE_PATH = "faiss_index_unicatt" # Dove salvare/caricare l'indice FAISS
MODEL_NAME_LLM = "gemini-1.5-flash-latest" # o "gemini-pro", "gemini-1.0-pro"
MODEL_NAME_EMBEDDINGS = "models/embedding-001" # Modello di embedding di Google
# -----------------------
```

**Importante**: Assicurati che MARKDOWN_DIR in chatbot.py corrisponda a OUTPUT_DIR in crawler.py.

## Utilizzo
### Fase 1: Eseguire il Crawler (crawler.py)
1. Apri un terminale nella directory del progetto.
2. Esegui il crawler:
```
python crawler.py
```
Lo script inizierà a scaricare le pagine e a salvarle come file Markdown nella directory output_markdown (o quella specificata in OUTPUT_DIR). Questo processo potrebbe richiedere del tempo a seconda della dimensione del sito e della profondità impostata. Verranno visualizzati dei log sull'avanzamento.

### Fase 2: Eseguire il Chatbot (chatbot.py)
Una volta che il crawler ha terminato e la directory output_markdown contiene i file .md:
1. Apri un terminale nella directory del progetto (puoi usare lo stesso).

2. Esegui il chatbot:

```
python chatbot.py
```

3. l'avvio, lo script ti chiederà se vuoi ricreare l'indice vettoriale:
4. La creazione dell'indice (se necessaria) potrebbe richiedere qualche minuto, a seconda del numero e della dimensione dei file Markdown.
5. Una volta pronto, scrivi le tue domande relative al contenuto dei documenti scaricati e premi Invio. Il chatbot utilizzerà i documenti e Gemini per generare una risposta.
6. Per uscire dal chatbot, digita esci o quit.

### Come Funziona il Chatbot (RAG)
Il chatbot.py implementa un pattern RAG (Retrieval Augmented Generation):
1. Caricamento e Divisione: I documenti Markdown vengono caricati e divisi in "chunk" (pezzi) più piccoli.
2. Embedding: Ogni chunk di testo viene convertito in un vettore numerico (embedding) utilizzando un modello di embedding di Google. Questo vettore rappresenta il significato semantico del chunk.
3. Indicizzazione (Vector Store): Gli embedding vengono memorizzati in un database vettoriale (FAISS in questo caso). Questo database permette di cercare rapidamente i chunk di testo più simili a una data query.
4. Recupero (Retrieval): Quando l'utente pone una domanda:
   * La domanda viene convertita in un embedding.
   * L'indice FAISS viene interrogato per trovare i chunk di testo i cui embedding sono più "vicini" (semanticamente simili) all'embedding della domanda. Questi sono i "documenti recuperati" o "contesto".
5. Generazione (Generation): I documenti recuperati (contesto) e la domanda originale dell'utente vengono forniti all'LLM (Google Gemini) attraverso un prompt specifico. Il prompt istruisce l'LLM a rispondere alla domanda basandosi esclusivamente sul contesto fornito.
6. Risposta: L'LLM genera una risposta che viene mostrata all'utente.
Questo approccio permette all'LLM di fornire risposte più accurate e basate sui fatti presenti nei documenti specifici, riducendo il rischio di "allucinazioni" (informazioni inventate).

### Considerazioni Etiche e Suggerimenti
* Etica del Crawling (crawler.py):
    * bots.txt: Questo crawler non implementa il parsing di robots.txt. Per un crawling responsabile, dovresti sempre controllare e rispettare le direttive del file robots.txt del sito target.
    * QUEST_DELAY: Il ritardo tra le richieste è impostato a 1 secondo per default. Aumentalo se necessario per essere più "gentile" con il server.
    * USER_AGENT: Fornisci un User-Agent descrittivo.
    * Costi API (chatbot.py): L'uso dei modelli Google Gemini tramite API comporta dei costi. Monitora il tuo utilizzo sulla console di Google Cloud o Google AI Studio. Il modello gemini-1.5-flash-latest è generalmente più economico di gemini-pro.
    * Qualità dell'Estrazione (crawler.py): L'euristica per estrarre il "contenuto principale" nel crawler è generica. Potrebbe essere necessario personalizzare i selettori CSS per il sito specifico per ottenere Markdown più puliti e pertinenti.
    * Qualità delle Risposte (chatbot.py): La qualità delle risposte del chatbot dipende dalla qualità dei documenti Markdown, dalla pertinenza dei chunk recuperati e dalla capacità dell'LLM. Sperimenta con chunk_size, chunk_overlap e il prompt per ottimizzare i risultati.

## Possibili Miglioramenti

Crawler:
Implementare il parsing di robots.txt.
Migliorare l'estrazione del contenuto principale.
Gestione più robusta degli errori e dei reindirizzamenti.

Chatbot:
Sperimentare con diversi modelli LLM o di embedding.
Migliorare il prompt per la generazione.
Implementare strategie di recupero più avanzate (es. HyDE, re-ranking).
Aggiungere un'interfaccia utente grafica (es. con Streamlit o Gradio).
Persistenza della cronologia della chat.




