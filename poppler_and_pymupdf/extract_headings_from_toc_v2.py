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
    dest: dict
    heading_found_in_text: bool = False
    text_before: str | None = None
    text_after: str | None = None


def extract_headings_from_toc(doc: pymupdf.Document) -> list[TableOfContentsEntry]:
    """
    Extract the headings (and associated metadata) from the table of contents of document `doc`.

    Approach:
        - For every table of contents entry, find that heading in the text (if it
            exists as a heading in the text) as follows:
            1. Iterate through all text elements on the page which the ToC element links to
            2. For every text element on that page containing the ToC text, save the size of
                that text element.
            3. The largest text element found is assumed to be the heading corresponding to
                the ToC element.

    Known Problems:
        - I'm currently using `if clean_toc_text == clean_line_text: ...` which is causing some
            headings to be missed. I was previously using
            `if clean_toc_text in clean_line_text: ...`, which was sometimes matching to the
            wrong heading e.g. "Act" matching "The POPI Act" prior to the actual "Act" heading.
    """
    toc_raw = doc.get_toc(simple=False)
    toc: list[TableOfContentsEntry] = [
        TableOfContentsEntry(
            heading_level=level, text=title, page_num=page, dest=dest
        )
        for level, title, page, dest in toc_raw
    ]
    for toc_item in toc:
        page: pymupdf.Page = doc.load_page(toc_item.page_num - 1)
        blocks: list[dict] = page.get_text("dict").get("blocks", [])

        clean_toc_text: str = unicodedata.normalize(
            "NFKC", " ".join(toc_item.text.split())
        ).lower()

        link_y_coord = None
        if toc_item.dest.get("kind") == pymupdf.LINK_GOTO:
            if "to" in toc_item.dest and toc_item.dest["to"]:
                link_y_coord = toc_item.dest["to"].y

        if link_y_coord is None:
            continue

        page_text = _merge_page_text_blocks(blocks)
        clean_page_text = unicodedata.normalize(
            "NFKC", " ".join(page_text.split())
        ).lower()
        if clean_toc_text not in clean_page_text:
            continue

        candidate_blocks = []
        for block_idx, block in enumerate(blocks):
            if block["type"] != 0:  # not a text block
                continue

            block_text = _get_text_from_block(block)
            if not block_text:
                continue

            clean_block_text: str = unicodedata.normalize(
                "NFKC", " ".join(block_text.split())
            ).lower()

            if clean_toc_text in clean_block_text:
                block_y_coord = block["bbox"][1]  # y0
                candidate_blocks.append(
                    {
                        "block_index": block_idx,
                        "distance": abs(block_y_coord - link_y_coord),
                    }
                )

        if candidate_blocks:
            best_match = min(candidate_blocks, key=lambda x: x["distance"])
            best_match_found_block_index = best_match["block_index"]
            toc_item.heading_found_in_text = True
            # find the first text block prior to the match #
            for block_idx in range(best_match_found_block_index - 1, -1, -1):
                block_text = _get_text_from_block(blocks[block_idx])
                if block_text and block_text.strip():
                    toc_item.text_before = block_text
                    break
            # find the first text block after the match #
            for block_idx in range(best_match_found_block_index + 1, len(blocks)):
                block_text = _get_text_from_block(blocks[block_idx])
                if block_text and block_text.strip():
                    toc_item.text_after = block_text
                    break

    return toc


def _merge_page_text_blocks(blocks: list[dict]) -> str:
    """Merge all text blocks on a page into a single string."""
    page_text = ""
    for block in blocks:
        if block.get("type") == 0:  # text block
            block_text = _get_text_from_block(block)
            if block_text:
                page_text += block_text + "\n"
    return page_text


def _get_text_from_block(block_dict: dict) -> str | None:
    """Extract the text from a PDF block."""
    if block_dict.get("type") == 0:  # text block
        parts = []
        for line in block_dict.get("lines", []):
            for span in line.get("spans", []):
                parts.append(span["text"])
        return " ".join(parts)
    return None
