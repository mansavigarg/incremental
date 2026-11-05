"""Persist policy embeddings in a cosine-distance Chroma collection."""

import json
from functools import lru_cache
from pathlib import Path


from config.constants import POLICY_CHUNK_CHARACTERS
from loanserve.retrieval.chunking import chunk_documents
from loanserve.retrieval.document_loader import load_policy_documents


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "policy_chunks"


@lru_cache(maxsize=1)
def load_embedder():
    from sentence_transformers import SentenceTransformer
    local_model = Path(__file__).resolve().parents[2] / "embedding_model"
    return SentenceTransformer(str(local_model) if local_model.exists() else EMBEDDING_MODEL_NAME)


def describe_chunks(chunks, manifest_path):
    manifest = {entry["document_id"]: entry for entry in json.loads(Path(manifest_path).read_text())}
    return [
        {"document_id": chunk["document_id"], "heading": chunk["heading"],
         "product_type": manifest[chunk["document_id"]]["product_type"],
         "category": manifest[chunk["document_id"]]["category"],
         "effective_date": manifest[chunk["document_id"]]["effective_date"]}
        for chunk in chunks
    ]


def build_policy_store(chunks, descriptions, store_path, embedder):
    import chromadb
    client = chromadb.PersistentClient(path=str(store_path))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[chunk["chunk_id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=descriptions,
        embeddings=embedder.encode([chunk["heading"] + ': ' + chunk["text"] for chunk in chunks], normalize_embeddings=True).tolist(),
    )
    return collection


def open_policy_store(store_path):
    import chromadb
    return chromadb.PersistentClient(path=str(store_path)).get_collection(COLLECTION_NAME)


def search_policy(collection, question, embedder, how_many, where=None):
    parameters = {
        "query_embeddings": embedder.encode([question], normalize_embeddings=True).tolist(),
        "n_results": how_many,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        parameters["where"] = where
    found = collection.query(**parameters)
    return [
        {"chunk_id": chunk_id, "text": text, "heading": metadata["heading"],
         "document_id": metadata["document_id"], "distance": distance}
        for chunk_id, text, metadata, distance in zip(
            found["ids"][0], found["documents"][0], found["metadatas"][0], found["distances"][0]
        )
    ]


if __name__ == "__main__":
    chunks = chunk_documents(load_policy_documents("data/policy_documents"), POLICY_CHUNK_CHARACTERS)
    metadata = describe_chunks(chunks, "data/policy_documents_manifest.json")
    collection = build_policy_store(chunks, metadata, "database/policy_store", load_embedder())
    print("chunks stored:", collection.count(), "distance:", collection.metadata)
