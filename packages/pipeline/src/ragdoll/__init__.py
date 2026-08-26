"""ragdoll — a platform for creating RAG pipelines.

Everything in this package runs on your machine. Parsing, chunking, indexing and
storage are local. The one exception is token counting, which asks the Claude API
because only the model's own tokenizer gives a trustworthy count.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
