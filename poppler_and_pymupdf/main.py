"""
CLI tool for extracting text from a PDF which has a contents section.
Text is extracted using poppler and headings from the PDF TableOfContents using pymupdf \
(and then the 2 results are combined).
"""

import argparse
import asyncio
from pathlib import Path

import pymupdf

from add_headings import add_headings
from extract_headings_from_toc_v3 import extract_headings_from_toc, TableOfContentsEntry
from pdftotext_async import pdftotext_async


def text_from_pdf():
    """
    TODO.
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-i", "--input", type=Path, help="path to PDF")
    arg_parser.add_argument("-o", "--output", type=Path, help="desired output path")
    args = arg_parser.parse_args()

    doc = pymupdf.open(args.input)
    print("extracting items from Table of Contents")
    toc: list[TableOfContentsEntry] = extract_headings_from_toc(doc)
    with open(args.input, "rb") as file:
        doc_content: bytes = file.read()

    print("extracting PDF text")
    doc_text: list[str] = asyncio.run(
        pdftotext_async(doc_content),
    )

    print("Annotating headings in document")
    doc_text_with_headings, headings_report = add_headings(
        doc_text=doc_text,
        toc=toc,
    )

    print("Exporting results")
    with open(args.output, "w", encoding="utf-8") as file:
        file.write(doc_text_with_headings)

    return headings_report


if __name__ == "__main__":
    process_report: dict = text_from_pdf()
