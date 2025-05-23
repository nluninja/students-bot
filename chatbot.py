import os
import shutil
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain
from langchain.memory import ChatMessageHistory

# --- Configurazione ---
MARKDOWN_DIR = "output_markdown"  # Directory con i file Markdown scaricati
VECTORSTORE_PATH = "faiss_index_unicatt" # Dove salvare/caricare l'indice FAISS
MODEL_NAME_LLM = "gemini-1.5-flash-latest" # o "gemini-pro"
MODEL_NAME_EMBEDDINGS = "models/embedding-001" # Modello di embedding standard di Google

# Carica le variabili d'ambiente (es. GOOGLE_API_KEY)
load_dotenv()

# Verifica che la API key sia impostata
if not os.getenv("GOOGLE_API_KEY"):
    print("Errore: La variabile d'ambiente GOOGLE_API_KEY non è impostata.")
    print("Per favore, crea un file .env con GOOGLE_API_KEY='LA_TUA_API_KEY'")
    exit()

def load_and_split_documents(directory_path):
    """Carica i documenti Markdown e li divide in chunk."""
    print(f"Caricamento documenti da: {directory_path}")
    # Puoi scegliere tra UnstructuredMarkdownLoader (più dettagliato) o TextLoader (più semplice)
    # loader = DirectoryLoader(directory_path, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader, show_progress=True)
    loader = DirectoryLoader(directory_path, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}, show_progress=True)

    try:
        documents = loader.load()
    except Exception as e:
        print(f"Errore durante il caricamento dei documenti: {e}")
        print("Assicurati che la cartella 'output_markdown' esista e contenga file .md validi.")
        return []

    if not documents:
        print("Nessun documento Markdown trovato nella directory specificata.")
        return []

    print(f"Caricati {len(documents)} documenti.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Dimensione dei chunk
        chunk_overlap=200, # Sovrapposizione tra chunk
        length_function=len
    )
    split_docs = text_splitter.split_documents(documents)
    print(f"Documenti divisi in {len(split_docs)} chunks.")
    return split_docs

def get_vectorstore(force_recreate=False):
    """Crea o carica un vectorstore FAISS."""
    embeddings_model = GoogleGenerativeAIEmbeddings(model=MODEL_NAME_EMBEDDINGS)

    if os.path.exists(VECTORSTORE_PATH) and not force_recreate:
        print(f"Caricamento vectorstore esistente da: {VECTORSTORE_PATH}")
        try:
            vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings_model, allow_dangerous_deserialization=True)
            print("Vectorstore caricato con successo.")
            return vectorstore
        except Exception as e:
            print(f"Errore nel caricamento del vectorstore: {e}. Provo a ricrearlo.")
            if os.path.exists(VECTORSTORE_PATH):
                shutil.rmtree(VECTORSTORE_PATH) # Rimuovi indice corrotto/vecchio

    print("Creazione di un nuovo vectorstore...")
    if not os.path.exists(MARKDOWN_DIR) or not os.listdir(MARKDOWN_DIR):
        print(f"La directory {MARKDOWN_DIR} è vuota o non esiste.")
        print("Esegui prima il crawler per scaricare i file Markdown.")
        return None

    documents = load_and_split_documents(MARKDOWN_DIR)
    if not documents:
        return None

    try:
        vectorstore = FAISS.from_documents(documents, embeddings_model)
        vectorstore.save_local(VECTORSTORE_PATH)
        print(f"Nuovo vectorstore creato e salvato in: {VECTORSTORE_PATH}")
        return vectorstore
    except Exception as e:
        print(f"Errore durante la creazione del vectorstore FAISS: {e}")
        return None

def create_rag_chain(vectorstore):
    """Crea la catena RAG."""
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME_LLM, temperature=0.3, convert_system_message_to_human=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # Recupera i 5 chunk più rilevanti

    # Prompt per la generazione della risposta basata sul contesto
    # Usiamo MessagesPlaceholder per la cronologia della chat
    system_prompt = (
        "Sei un assistente AI. Usa i seguenti documenti recuperati (contesto) per rispondere alla domanda. "
        "Se non conosci la risposta basandoti sul contesto fornito, dillo chiaramente. "
        "Non inventare informazioni. Rispondi in italiano."
        "\n\n"
        "<context>\n{context}\n</context>"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )

    # Catena per "riempire" il prompt con i documenti recuperati
    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    # Catena completa che prima recupera i documenti e poi li passa alla question_answer_chain
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain

def main_chat():
    """Funzione principale per avviare il chatbot."""
    print("Inizializzazione di StudentsBot...")

    # Chiedi se ricreare l'indice
    recreate_choice = input(f"Vuoi ricreare l'indice da '{MARKDOWN_DIR}'? (s/N): ").lower()
    force_recreate_index = recreate_choice == 's'

    vectorstore = get_vectorstore(force_recreate=force_recreate_index)
    if not vectorstore:
        print("Impossibile inizializzare il vectorstore. Uscita.")
        return

    rag_chain = create_rag_chain(vectorstore)
    chat_history = ChatMessageHistory()

    print("\nChatbot pronto! Digita 'esci' o 'quit' per terminare.")
    print("----------------------------------------------------")

    while True:
        try:
            query = input("Tu: ")
            if query.lower() in ["esci", "quit", "exit"]:
                print("Chatbot: Arrivederci!")
                break
            if not query.strip():
                continue

            print("Chatbot: Sto pensando...")

            # Invoca la catena RAG con la query e la cronologia
            response = rag_chain.invoke({
                "input": query,
                "chat_history": chat_history.messages
            })

            answer = response.get("answer", "Non ho trovato una risposta.")
            print(f"Chatbot: {answer}")

            # Aggiorna la cronologia della chat
            chat_history.add_user_message(query)
            chat_history.add_ai_message(answer)

            # Opzionale: mostra i documenti sorgente recuperati
            # if "context" in response and response["context"]:
            #     print("\n--- Documenti Sorgente Recuperati ---")
            #     for i, doc in enumerate(response["context"][:2]): # Mostra i primi 2
            #         print(f"Sorgente {i+1}: {doc.metadata.get('source', 'N/D')} (Estratto: {doc.page_content[:100]}...)")
            #     print("-------------------------------------\n")

        except Exception as e:
            print(f"Si è verificato un errore: {e}")
        print("----------------------------------------------------")


if __name__ == "__main__":
    main_chat()