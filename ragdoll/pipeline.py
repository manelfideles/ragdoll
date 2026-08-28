import os
from dataclasses import dataclass

import polars as pl
import pymupdf as pdf
from dotenv import load_dotenv
from google import genai

load_dotenv()

EMBEDDING_MODEL = ""
CHAT_MODEL = "gemini-3.5-flash-lite"
LLM_API_KEY = os.getenv("GEMINI_API_KEY")
KEYWORD_SYSTEM_PROMPT = """
Provide 3 to 5 short keywords (not expressions or sentences) useful for searching the following query: "{}". 
Guidelines:
- Do not repeat keywords
- Reply **only** with the keywords
- Return the text separated by simple whitespace, not \n or \t.
"""


def llm_client() -> genai.Client:
    client = genai.Client(api_key=LLM_API_KEY)
    return client


def open_document(path: str) -> pdf.Document:
    return pdf.open(path)


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    query: str

    @property
    def normalized_query(self) -> str:
        """
        The normalized query.
        """
        # Placeholder until I find a simple normalization method
        return self.query

    def get_keywords(self, client: genai.Client) -> list[str]:
        """
        The most useful keywords for searching a document.
        Short phrases the document is likely to contain,
        not necessarily the literal words of the question.
        """
        # Calls a LLM to fetch the keywords
        prompt = KEYWORD_SYSTEM_PROMPT.format(self.normalized_query)
        print(prompt)
        contents = client.models.generate_content(
            model=CHAT_MODEL, contents=prompt
        ).text
        keywords = contents.split(" ")
        return keywords


def parse_query(raw_query: str) -> ParsedQuery:
    return ParsedQuery(raw_query)


def parse_document(document: pdf.Document) -> pl.DataFrame:
    """
    Outputs a dataframe where each row contains the text and positioning metadata.
    This doesn’t:
    - Detect tables (Table 1 page 4, Table 3 page 9 flatten into plain lines);
    - Reconstruct headings, footnotes, or cross-references;
    - Handle multi-column layouts.
    """
    data = []
    for page_idx, page in enumerate(document):
        blocks = page.get_text("dict").get("blocks", [])
        line_num = 0
        for block in blocks:
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            for line in lines:
                spans = line.get("spans", [])
                if not spans:
                    continue

                text = "".join(s["text"] for s in spans)
                rect = pdf.Rect(spans[0]["bbox"])
                for span in spans[1:]:
                    rect |= pdf.Rect(span["bbox"])

                data.append(
                    {
                        "page_num": page_idx + 1,
                        "line_num": line_num + 1,
                        "text": text,
                        "x0": float(rect.x0),
                        "y0": float(rect.y0),
                        "x1": float(rect.x1),
                        "y1": float(rect.y1),
                    }
                )
                line_num += 1
    return pl.DataFrame(data)


def pipeline(query: str, path: str):
    # client = llm_client()
    # parsed_query = parse_query(query)
    # parsed_query.get_keywords(client)
    doc = open_document(path)
    parsed_doc = parse_document(doc)


if __name__ == "__main__":
    query = "What is 'feeling the water'?"
    path = "/Users/fideles/Desktop/learning/ragdoll/corpus/swim-smooth.pdf"
    pipeline(query, path)
