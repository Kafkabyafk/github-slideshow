#!/usr/bin/env python3
"""pdf2txt — PDF -> raw .txt via OCR (works on scanned / copy-protected PDFs).

Renders each page to an image and OCRs it with Tesseract, so it works even when
the PDF has no text layer (the "around the copyright problem" path). For PDFs
that DO have a clean text layer you can pass --prefer-text to skip OCR.

Usage:
    python pdf2txt.py reading.pdf                 # -> reading.raw.txt
    python pdf2txt.py somefolder/ --out out/      # every *.pdf in folder
    python pdf2txt.py reading.pdf --dpi 300 --prefer-text
"""
import argparse, glob, os, re, subprocess, tempfile
import fitz  # pymupdf


def ocr_pdf(path, dpi, prefer_text):
    doc = fitz.open(path)
    # fast path: use embedded text layer if it's clearly present
    if prefer_text:
        txt = "\n".join(doc[i].get_text() for i in range(doc.page_count))
        if len(txt.strip()) > 200 * doc.page_count / 10:
            return txt
    pages = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    with tempfile.TemporaryDirectory() as td:
        for i in range(doc.page_count):
            png = os.path.join(td, f"p{i:03d}.png")
            doc[i].get_pixmap(matrix=mat).save(png)
            base = png[:-4]
            subprocess.run(["tesseract", png, base, "--psm", "6"],
                           check=True, capture_output=True)
            pages.append(open(base + ".txt").read())
    return "\n".join(pages)


def light_clean(text):
    """Light de-noise only — join hyphen line-breaks, drop blank-heavy runs.
    (Heavy cleanup/normalization is textprep.py's job.)"""
    text = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", text)   # de-hyphenate line breaks
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="a .pdf file or a folder of PDFs")
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--prefer-text", action="store_true",
                    help="use the embedded text layer when present instead of OCR")
    a = ap.parse_args()

    pdfs = ([a.input] if a.input.lower().endswith(".pdf")
            else sorted(f for f in glob.glob(os.path.join(a.input, "**/*.pdf"), recursive=True)
                        if "__MACOSX" not in f))
    os.makedirs(a.out, exist_ok=True)
    for p in pdfs:
        name = os.path.splitext(os.path.basename(p))[0]
        dst = os.path.join(a.out, name + ".raw.txt")
        print(f"OCR  {os.path.basename(p)} ...", flush=True)
        open(dst, "w").write(light_clean(ocr_pdf(p, a.dpi, a.prefer_text)))
        print(f"  -> {dst}")


if __name__ == "__main__":
    main()
