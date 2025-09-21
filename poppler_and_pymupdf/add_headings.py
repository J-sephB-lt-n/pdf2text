"""
TODO.
"""

import statistics
from dataclasses import asdict
from enum import Enum

from extract_headings_from_toc_v3 import TableOfContentsEntry


class TocItemStatus(Enum):
    SUCCESS = "SUCCESS: found ToC item in extracted document text"
    FAILED_TOC_ITEM_NOT_FOUND = (
        "FAILED: ToC item text does not appear at all in target page text "
        "(during ToC extraction step)",
    )
    FAILED_TOC_ITEM_NOT_MATCHED = (
        "FAILED: ToC item found in document text during ToC parsing step but "
        "not found when matching to extracted document text."
    )


def jaccard_sim(set1: set[str], set2: set[str]) -> float:
    """Calculates the Jaccard similarity [0.0, 1.0] between two sets of strings."""
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)


def add_headings(
    doc_text: list[str],
    toc: list[TableOfContentsEntry],
) -> tuple[str, dict]:
    """
    TODO.

    Returns:
        tuple[
            str,    # input `doc_text` with headings annotated
            dict    # process report
        ]
    """
    process_report: dict = {
        "status_counts": {
            TocItemStatus.SUCCESS.value: 0,
            TocItemStatus.FAILED_TOC_ITEM_NOT_FOUND.value: 0,
            TocItemStatus.FAILED_TOC_ITEM_NOT_MATCHED.value: 0,
        },
        "per_toc_item": [],
    }
    for toc_item in toc:
        if not toc_item.heading_found_in_text:
            process_report["status_counts"][
                TocItemStatus.FAILED_TOC_ITEM_NOT_FOUND.value
            ] += 1
            process_report["per_toc_item"].append(
                {"status": TocItemStatus.FAILED_TOC_ITEM_NOT_FOUND.value}
                | asdict(toc_item)
            )
            continue

        page_text: str = doc_text[toc_item.page_num - 1]
        page_text_lines: list[str] = page_text.splitlines(keepends=True)
        potential_heading_locations: list[int] = [
            idx for idx, line in enumerate(page_text_lines) if toc_item.text in line
        ]
        if not potential_heading_locations:
            process_report["status_counts"][
                TocItemStatus.FAILED_TOC_ITEM_NOT_MATCHED.value
            ] += 1
            process_report["per_toc_item"].append(
                {"status": TocItemStatus.FAILED_TOC_ITEM_NOT_MATCHED.value}
                | asdict(toc_item)
            )
            continue

        potential_heading_location_scores: list[float] = []
        for loc in potential_heading_locations:
            individ_scores: list[float] = []
            if toc_item.text_before and loc != 0:
                text_before_words: list[str] = [
                    word
                    for word in "".join(page_text_lines[:loc]).split()
                    if word.strip()
                ]
                toc_before_words: list[str] = [
                    word
                    for word in toc_item.text_before.strip().split()
                    if word.strip()
                ]
                text_before_words = text_before_words[-len(toc_before_words) :]
                individ_scores.append(
                    jaccard_sim(set(text_before_words), set(toc_before_words)),
                )

            text_words: list[str] = [
                word for word in page_text_lines[loc].split() if word.strip()
            ]
            toc_words: list[str] = [
                word for word in toc_item.text.split() if word.strip()
            ]
            individ_scores.append(
                jaccard_sim(set(text_words), set(toc_words)),
            )

            if toc_item.text_after and loc + 1 != len(page_text_lines):
                text_after_words: list[str] = [
                    word
                    for word in "".join(page_text_lines[loc + 1 :]).split()
                    if word.strip()
                ]
                toc_after_words: list[str] = [
                    word for word in toc_item.text_after.split() if word.strip()
                ]
                text_after_words = text_after_words[: len(toc_after_words)]
                individ_scores.append(
                    jaccard_sim(set(text_after_words), set(toc_after_words)),
                )

            potential_heading_location_scores.append(
                statistics.mean(individ_scores),
            )

        max_score: float = max(potential_heading_location_scores)
        max_score_idx: int = potential_heading_location_scores.index(max_score)
        heading_location: int = potential_heading_locations[max_score_idx]
