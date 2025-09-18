"""
Function to extract the headings (and their levels and other metadata)
from the Table of Contents in the PDF.
"""

from dataclasses import dataclass

import pymupdf
import unicodedata


@dataclass
class TableOfContentsEntry:
    """A single item in the Table of Contents."""

    heading_level: int
    text: str
    page_num: int
    heading_found_in_text: bool = False
    text_before: str | None = None
    text_after: str | None = None


def extract_headings_from_toc(doc: pymupdf.Document) -> list[TableOfContentsEntry]:
    """
    Extract the headings (and associated metadata) from `doc`.

    Approach:
        - For every table of contents entry, find that heading in the text (if it
            exists as a heading in the text) as follows:
            1. Iterate through all text elements on the page which the ToC element links to
            2. For every text element on that page containing the ToC text, save the size of
                that text element.
            3. The largest text element found is assumed to be the heading corresponding to
                the ToC element.
    """
    toc: list[TableOfContentsEntry] = [TableOfContentsEntry(*x) for x in doc.get_toc()]
    for toc_item in toc:
        page: pymupdf.Page = doc.load_page(toc_item.page_num - 1)
        blocks: list[dict] = page.get_text("dict").get("blocks", [])

        clean_toc_text: str = unicodedata.normalize(
            "NFKC", " ".join(toc_item.text.split())
        ).lower()

        best_match_found: dict = {"block_index": None, "font_size": -99}

        for (
            block_idx,
            block,
        ) in enumerate(blocks):
            if block["type"] != 0:  # not a text block
                continue

            for line in block.get("lines", []):
                line_spans = line.get("spans", [])
                if not line_spans:
                    continue

                line_text = "".join(span["text"] for span in line_spans)
                clean_line_text: str = unicodedata.normalize(
                    "NFKC", " ".join(line_text.split())
                ).lower()

                if clean_toc_text in clean_line_text:
                    toc_item.heading_found_in_text = True
                    # find biggest font size on this line #
                    max_font_in_line: float = 0.0
                    for span in line_spans:
                        max_font_in_line = max(max_font_in_line, span["size"])

                    if max_font_in_line > best_match_found["font_size"]:
                        best_match_found["block_index"] = block_idx
                        best_match_found["font_size"] = max_font_in_line

        if toc_item.heading_found_in_text:
            # find the first text block prior to the match #
            for block_idx in range(best_match_found["block_index"] - 1, -1, -1):
                block_text = _get_text_from_block(blocks[block_idx])
                if block_text and block_text.strip():
                    toc_item.text_before = block_text
                    break
            # find the first text block after the match #
            for block_idx in range(best_match_found["block_index"] + 1, len(blocks)):
                block_text = _get_text_from_block(blocks[block_idx])
                if block_text and block_text.strip():
                    toc_item.text_after = block_text
                    break

    return toc


def _get_text_from_block(block_dict: dict) -> str | None:
    """Extract the text from a PDF block."""
    if block_dict.get("type") == 0:  # text block
        parts = []
        for line in block_dict.get("lines", []):
            for span in line.get("spans", []):
                parts.append(span["text"])
        return " ".join(parts)
    return None
