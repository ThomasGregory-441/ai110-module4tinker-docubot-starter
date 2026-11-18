"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on", "or",
    "the", "to", "what", "which", "where", "who", "with",
    "system", "project", "application", "documentation",
}

WORD_NORMALIZATION = {
    "authentication": "auth",
    "authenticate": "auth",
    "generated": "generate",
    "generation": "generate",
    "created": "generate",
    "create": "generate",
}


def _normalize_words(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    normalized = set()

    for word in words:
        if word in STOP_WORDS:
            continue

        word = WORD_NORMALIZATION.get(word, word)

        if word.endswith("s") and len(word) > 3:
            word = word[:-1]

        normalized.add(word)

    return normalized

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")

        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()

                filename = os.path.basename(path)
                docs.append((filename, text))

        return docs

    # -----------------------------------------------------------
    # Index Construction
    # -----------------------------------------------------------

    def build_index(self, documents):
        """Map normalized words to the filenames where they appear."""
        index = {}

        for filename, text in documents:
            for word in _normalize_words(text):
                index.setdefault(word, []).append(filename)

        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """Score text by the number of normalized query words it contains."""
        return len(_normalize_words(query) & _normalize_words(text))

    def retrieve(self, query, top_k=3):
        """Return the best matching paragraph snippets with headings attached."""
        query_words = _normalize_words(query)

        if not query_words:
            return []

        candidate_files = set()
        for word in query_words:
            candidate_files.update(self.index.get(word, []))

        scored_results = []

        for filename, text in self.documents:
            if filename not in candidate_files:
                continue

            raw_paragraphs = [
                paragraph.strip()
                for paragraph in re.split(r"\n\s*\n", text)
                if paragraph.strip()
            ]

            paragraphs = []
            i = 0

            while i < len(raw_paragraphs):
                paragraph = raw_paragraphs[i]

                if (
                    paragraph.startswith("#")
                    and i + 1 < len(raw_paragraphs)
                    and not raw_paragraphs[i + 1].startswith("#")
                ):
                    paragraph += "\n" + raw_paragraphs[i + 1]
                    i += 1

                paragraphs.append(paragraph)
                i += 1

            for paragraph in paragraphs:
                score = self.score_document(query, paragraph)

                if score > 0:
                    scored_results.append((score, filename, paragraph))

        scored_results.sort(key=lambda result: result[0], reverse=True)

        return [
            (filename, paragraph)
            for score, filename, paragraph in scored_results[:top_k]
        ]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Retrieval-only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []

        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        RAG mode.
        Uses retrieval to select snippets, then asks Gemini to answer
        using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Helper for Naive LLM Mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into one string.
        Used by Naive LLM mode.
        """
        return "\n\n".join(text for _, text in self.documents)