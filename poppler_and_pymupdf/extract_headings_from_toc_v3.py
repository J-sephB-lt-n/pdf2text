"""
Function to extract the headings (and their levels and other metadata)
from the Table of Contents in the PDF.
"""

from dataclasses import dataclass
from typing import Literal

import pymupdf
import unicodedata


@dataclass
class TableOfContentsEntry:
    """A single item in the Table of Contents."""

    heading_level: int
    text: str
    page_num: int
    link_data: dict
    heading_found_in_text: bool = False
    match_reason: (
        Literal[
            "SINGLE_PERFECT_MATCH",
            "LARGEST_FONT_PERFECT_MATCH",
            "APPROX_MATCH_CLOSEST_TO_TARGET",
            "NO_MATCH",
        ]
        | None
    ) = None
    text_before: str | None = None
    text_after: str | None = None


def normalise_lookup_text(input_text: str) -> str:
    """Return a simplified form of `input_text`, helping make text matches more lenient."""
    return (
        unicodedata.normalize(
            "NFKC",
            " ".join(input_text.split()),
        )
        .lower()
        .strip()
    )


def extract_headings_from_toc(doc: pymupdf.Document) -> list[TableOfContentsEntry]:
    """
    Extract the headings (and associated metadata) from the table of contents of document `doc`.

    Approach:
        - For every item in the Table of Contents (ToC), find the heading that it is pointing to in
          the text on the target page (if it exists there) as follows:
            1. Find all text blocks on the target page which contain the same text as the ToC item
            2. If there is exactly 1 block containing only that Toc item text, then that is assumed
                to be the heading.
            3. If there are multiple text blocks containing precisely that ToC item text, then the
                text block whose font is largest is assumed to be the heading.
            4. If there are multiple text blocks which simply contain the ToC item text (alongside
                other text), then the one whose start y-coordinate is closest to the target
                y-coordinate of the ToC item link is assumed to be the target heading.
    """
    toc: list[TableOfContentsEntry] = [
        TableOfContentsEntry(*x) for x in doc.get_toc(simple=False)
    ]
    for toc_item in toc:
        page: pymupdf.Page = doc.load_page(toc_item.page_num - 1)

        blocks: list[dict] = page.get_text("dict").get("blocks", [])
        blocks = [b for b in blocks if b["type"] == 0]  # only keep text blocks

        for block in blocks:
            block_text_items: list[str] = []
            max_font_size_in_block: float = 0.0
            for line in block["lines"]:
                for span in line["spans"]:
                    max_font_size_in_block = max(span["size"], max_font_size_in_block)

                    block_text_items.append(span["text"])
            block["max_font_size_in_block"] = max_font_size_in_block
            block["full_block_text"] = " ".join(block_text_items).strip()

        toc_item_text_lookup: str = normalise_lookup_text(toc_item.text)
        for block in blocks:
            block["match_checks"] = {}
            block_text_lookup: str = normalise_lookup_text(block["full_block_text"])
            if toc_item_text_lookup == block_text_lookup:
                block["match_checks"]["toc_text_matches_exactly"] = True
                block["match_checks"]["contains_toc_text"] = True
            elif toc_item_text_lookup in block_text_lookup:
                block["match_checks"]["toc_text_matches_exactly"] = False
                block["match_checks"]["contains_toc_text"] = True
            else:
                block["match_checks"]["toc_text_matches_exactly"] = False
                block["match_checks"]["contains_toc_text"] = False

        exact_match_blocks: list[dict] = [
            b for b in blocks if b["match_checks"]["toc_text_matches_exactly"]
        ]

        if len(exact_match_blocks) == 1:
            toc_item.heading_found_in_text = True
            toc_item.match_reason = "SINGLE_PERFECT_MATCH"

    return toc
