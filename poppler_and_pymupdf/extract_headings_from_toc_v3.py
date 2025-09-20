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
    matching_page_text: str | None = None
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
                text block whose font is largest is assumed to be the heading (taking the first one
                in the case of a tie).
            4. If there are multiple text blocks which simply contain the ToC item text (alongside
                other text), then the one whose start y-coordinate is closest to the target
                y-coordinate of the ToC item link is assumed to be the target heading.
                NOTE: named links (pymupdf.LINK_NAMED) are not handled.

    """
    toc: list[TableOfContentsEntry] = [
        TableOfContentsEntry(*x) for x in doc.get_toc(simple=False)
    ]
    for toc_item in toc:
        page: pymupdf.Page = doc.load_page(toc_item.page_num - 1)

        blocks: list[dict] = page.get_text("dict", sort=True).get("blocks", [])
        blocks = [b for b in blocks if b["type"] == 0]  # only keep text blocks

        for block_idx, block in enumerate(blocks):
            block["block_index"] = block_idx
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

        if exact_match_blocks:
            # Sort by font size (largest first), then by block index (smallest first) to break ties
            exact_match_blocks.sort(
                key=lambda b: (-b["max_font_size_in_block"], b["block_index"])
            )
            matched_block: dict = exact_match_blocks[0]
            toc_item.heading_found_in_text = True
            toc_item.match_reason = (
                "SINGLE_PERFECT_MATCH"
                if len(exact_match_blocks) == 1
                else "LARGEST_FONT_PERFECT_MATCH"
            )
            toc_item.matching_page_text = matched_block["full_block_text"]
            if matched_block["block_index"] != 0:
                toc_item.text_before = blocks[matched_block["block_index"] - 1][
                    "full_block_text"
                ]
            if matched_block["block_index"] + 1 < len(blocks):
                toc_item.text_after = blocks[matched_block["block_index"] + 1][
                    "full_block_text"
                ]

            continue  # next toc_item

        containing_blocks: list[dict] = [
            b for b in blocks if b["match_checks"]["contains_toc_text"]
        ]

        if containing_blocks:
            target_y: float | None = None
            # Every ToC entry has link data; for links to other parts of the same document,
            # this link data includes the y-coordinate of the destination on the page.
            if toc_item.link_data.get("kind") == pymupdf.LINK_GOTO:
                destination_point: pymupdf.Point = toc_item.link_data.get("to")
                if destination_point:
                    target_y = destination_point.y

            if target_y is not None:
                containing_blocks.sort(
                    key=lambda b, y=target_y: abs(
                        b["bbox"][1] - y,
                    ),
                )

            matched_block = containing_blocks[0]
            toc_item.heading_found_in_text = True
            toc_item.match_reason = "APPROX_MATCH_CLOSEST_TO_TARGET"
            toc_item.matching_page_text = matched_block["full_block_text"]
            if matched_block["block_index"] != 0:
                toc_item.text_before = blocks[matched_block["block_index"] - 1][
                    "full_block_text"
                ]
            if matched_block["block_index"] + 1 < len(blocks):
                toc_item.text_after = blocks[matched_block["block_index"] + 1][
                    "full_block_text"
                ]

            continue  # next toc_item

        toc_item.match_reason = "NO_MATCH"

    return toc
