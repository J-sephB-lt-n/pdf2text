"""
CLI tool for extracting text from a PDF which has a contents section.
Text is extracted using poppler and headings from the PDF TableOfContents using pymupdf \
(and then the 2 results are combined).
"""

import argparse
from pathlib import Path

import pymupdf

from extract_headings_from_toc_v3 import extract_headings_from_toc, TableOfContentsEntry


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-i", "--input", type=Path, help="path to PDF")
    arg_parser.add_argument("-o", "--output", type=Path, help="desired output path")
    args = arg_parser.parse_args()

    doc = pymupdf.open(args.input)
    toc: list[TableOfContentsEntry] = extract_headings_from_toc(doc)


if __name__ == "__main__":
    main()
