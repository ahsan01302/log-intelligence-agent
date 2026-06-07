from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://host.docker.internal:11434"
)

VECTOR_PATH = "/app/vectorstore"

def create_vector_store(log_lines):

    vector_store = FAISS.from_texts(
        texts=log_lines,
        embedding=embeddings
    )

    vector_store.save_local(VECTOR_PATH)

    return vector_store


def search_logs(query, k=3):

    vector_store = FAISS.load_local(
        VECTOR_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    results = vector_store.similarity_search(
        query,
        k=k
    )

    return results