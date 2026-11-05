"""Read every page of every supplied policy PDF."""

from pathlib import Path



def read_document_text(pdf_path):
    from pypdf import PdfReader
    pages = (page.extract_text() for page in PdfReader(str(pdf_path)).pages)
    return "\n".join(page for page in pages if page)


def load_policy_documents(folder_path):
    return [
        {"document_id": path.stem, "text": read_document_text(path)}
        for path in sorted(Path(folder_path).glob("*.pdf"))
    ]


if __name__ == "__main__":
    documents = load_policy_documents("data/policy_documents")
    print("documents:", len(documents), "characters:", sum(len(item["text"]) for item in documents))
