# RAG Glossary — `ragdoll`

The canonical language for this workspace. Every explainer, exercise and learning record uses these
terms. A term appears here only after Manuel has used it correctly, not when it was first taught.

## Core pipeline

**RAG (Retrieval-Augmented Generation)**:
Searching a document set for the passages that match a question, then answering from those passages.
A search technique with a language model on the end.
_Avoid_: AI search, semantic search, knowledge base AI

**Token**:
A piece of a word, and the unit models are billed and limited in. Roughly 750 words make 1,000 tokens.

**Chunk**:
One small piece of a document, indexed and retrieved as a unit.
_Avoid_: Passage, snippet, fragment, node

**Embedding**:
A vector that records the meaning of a piece of text, so that similar meanings sit close together.
_Avoid_: Vector representation, encoding, semantic fingerprint

**BM25**:
A keyword-scoring algorithm that ranks text by literal word matches. Precise where embeddings blur,
which is why it survives alongside them.
_Avoid_: Keyword search, lexical search, full-text search, TF-IDF

**Hybrid search**:
Running an embedding search and a BM25 search over the same chunks, then merging the two ranked lists.
_Avoid_: Combined search, dual retrieval

**Rank fusion**:
Merging two or more ranked result lists into one ordered list.

**Reranking**:
A second, slower scoring pass that takes a wide retrieval result, perhaps 150 chunks, and keeps the
best few. Buys accuracy without paying to put every candidate in the prompt.

**Contextual retrieval**:
Prepending 50 to 100 model-written tokens to each chunk, explaining where the chunk sits in its
document, before embedding and indexing it. Cut Anthropic's retrieval failure rate by 35%.
_Avoid_: Context injection, chunk enrichment, contextual chunking
