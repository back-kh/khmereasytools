# Simple KhmerRAG

`KhmerRAG` connects the existing local Khmer BM25 search to an optional answer
generator. The default needs no extra packages, embeddings, vector database,
model download, credentials or network access. It suits a small collection of
notes, OCR text and everyday documents.

```python
from khmereasytools import KhmerRAG

documents = {
    "school-notes": "សិស្សអានសៀវភៅនៅសាលារៀន។",
    "food-notes": "ខ្ញុំញ៉ាំបាយ។",
}
rag = KhmerRAG(documents)
result = rag.ask("សៀវភៅ")
print(result.context)  # [1] followed by the retrieved source passage.
assert result.answer is None  # Retrieval only until you supply a generator.
for source in result.sources:
    assert documents[source.document_id][source.start:source.end] == source.text
```

To generate answers with already downloaded local Qwen weights, configure a
local Ollama server, then pass an explicit client:

```python
from khmereasytools import LocalModel, KhmerRAG, khrag

model = LocalModel("qwen2.5:3b", timeout=120, max_tokens=1024)
rag = KhmerRAG(documents, generator=model)
result = rag.ask("សៀវភៅ")
print(result.answer)
print(result.sources)  # Always inspect the actual evidence behind [1], [2], ...
# Convenience form; reuse an index for repeated questions:
same = khrag("សៀវភៅ", rag)
```

The example model name illustrates setup; no Khmer answer-quality benchmark or
model recommendation is implied. Set `OLLAMA_NO_CLOUD=1` on the **Ollama server**
and restart it to disable cloud features; install/download weights separately
before offline use. See [Ollama's official local-only setup](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
`LocalModel` accepts only a loopback origin, bypasses environment HTTP proxies,
refuses redirects and never falls back to Google. Localhost alone does not prove
that a separately managed server cannot relay requests elsewhere. The client
follows the official [Ollama chat API](https://docs.ollama.com/api/chat).

For images and PDFs, extract text explicitly with KET-OCR first:

```python
from khmereasytools import ket_ocr, KhmerRAG

text = ket_ocr("document.pdf", lang="khm+eng")  # Optional [ocr] setup.
rag = KhmerRAG({"document.pdf": text})
```

Offsets in this example refer to the extracted text, not positions in the PDF.
Use `khanalyze` if you also need page-local layout boxes.

For page-specific source IDs, build the collection from individual page results:

```python
from khmereasytools import khanalyze, KhmerRAG

document = khanalyze("document.pdf", lang="khm+eng", segment=False)
rag = KhmerRAG({"document.pdf#page-{}".format(page.number): page.layout.text
                for page in document.pages})
```

When the local model runs on your own GPU server, forward its Ollama port over
SSH and use the loopback URL. Local-only configuration must apply on that server.
The toolkit does not install or start a remote model runtime.

```bash
# UTF-8 text files; retrieval only:
khmereasytools rag "សៀវភៅ" notes.txt other.txt
# Explicit local answer generation:
khmereasytools rag "សៀវភៅ" notes.txt --model qwen2.5:3b
```

## Behavior and limits

- Collections are a snapshot of a string/integer-ID-to-text mapping, or an
  iterable of texts with zero-based integer IDs. Rebuild after editing sources.
- Literal passages default to about 800 code points with 80-character overlap;
  `chunk_size` and `overlap` are configurable on the class. Nearby newlines are
  preferred; combining marks and Khmer coeng/joiner sequences stay with their
  bases. An unusually long indivisible combining sequence can exceed the target.
- `retrieve(question, limit=3)` returns ranked `RAGSource` tuples: citation
  number, document ID, start/end, literal text and BM25 score. Scores are not
  confidence values. Overlapping passages can come from the same document.
- `ask()` calls a supplied generator once only when a passage matches. With no
  model or no matches it returns `answer=None`, `generated=False`, and the
  available sources. Empty questions return no matches.
- A custom generator is a callable taking a prompt and returning nonempty text.
  It controls its own runtime and data handling. The built-in local client has
  bounded requests/output and rejects incomplete or truncated model responses.
- The prompt requests answers from the evidence, numbered citations, and
  abstention when the answer is missing. It treats source text as data. These
  instructions cannot guarantee model compliance or prevent hallucinations.
  Returned sources certify retrieval provenance, not generated claims.
- Keyword matching cannot guarantee that the answer is present, recognize all
  synonyms, correct OCR mistakes or search across languages automatically.
  There are no relevance judgments or end-to-end RAG accuracy results yet.

Unit/integration tests cover retrieval, source offsets, chunk coverage, citation
mapping, no-match behavior, CLI output, and the local HTTP contract. They do not
measure Khmer question-answering or translation quality.
