"""
Extract text from PDF `doc_bytes` (asynchronously) using poppler 'pdftotext'.
"""

import asyncio


async def pdftotext_async(doc_content: bytes) -> str:
    """Extract text from PDF `doc_bytes` (asynchronously) using poppler 'pdftotext'."""
    proc = await asyncio.create_subprocess_exec(
        "pdftotext",
        "-enc",
        "UTF-8",
        "-eol",
        "unix",
        # "-nopgbrk",
        "-layout",
        "-",
        "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(doc_content)
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext returned (error) returncode {proc.returncode}")

    return stdout.decode("utf-8")
