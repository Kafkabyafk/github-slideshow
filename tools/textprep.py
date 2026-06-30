#!/usr/bin/env python3
"""textprep — normalize raw text into Kokoro-ready form.

One sentence per line (so every chunk stays under Kokoro's 510-token limit,
since KPipeline splits on newlines), with numbers, symbols, and abbreviations
spelled out so the misaki G2P never has to guess.

Usage:
    python textprep.py in.txt out.txt
    from textprep import to_kokoro_lines      # use as a library
"""
import re, sys
from num2words import num2words

MAX_LINE = 300  # chars; keeps each chunk safely below 510 phoneme tokens
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def _spell_decimal(m):
    whole, frac = m.group(1), m.group(2)
    return num2words(int(whole)) + " point " + " ".join(num2words(int(d)) for d in frac)


def normalize(text):
    # straighten quotes / dashes
    text = (text.replace("’", "'").replace("‘", "'")
                .replace("“", '"').replace("”", '"')
                .replace("—", ", ").replace("–", ", ").replace(" - ", ", "))
    # symbols
    text = text.replace("%", " percent")
    text = re.sub(r"\s*&\s*", " and ", text)
    # abbreviations (dotted / longest first)
    for pat, rep in [
        (r"\bPh\.?D\.?", "doctorate"), (r"\bU\.S\.A\.", "United States"),
        (r"\bU\.S\.", "United States"), (r"\bi\.e\.,?", "that is,"),
        (r"\be\.g\.,?", "for example,"), (r"\betc\.", "and so on"),
        (r"\bvs\.", "versus"), (r"\bPR\b", "proportional representation"),
        (r"\bIQ\b", "I.Q."),
    ]:
        text = re.sub(pat, rep, text)
    # numbers (order matters)
    text = re.sub(r"\b(\d+)\.(\d+)\b", _spell_decimal, text)                         # 25.72
    text = re.sub(rf"\b({MONTHS})\s+(\d{{1,2}})\b",                                   # March 20  (day only)
                  lambda m: f"{m.group(1)} {num2words(int(m.group(2)), to='ordinal')}", text)
    text = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b",                                        # 17th
                  lambda m: num2words(int(m.group(1)), to="ordinal"), text)
    text = re.sub(r"\b(?:19|20)\d{2}\b", lambda m: num2words(int(m.group(0)), to="year"), text)  # years
    text = re.sub(r"\b\d+\b", lambda m: num2words(int(m.group(0))), text)            # remaining ints
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _is_heading(line):
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(line) < 60


def _split_sentences(text):
    text = re.sub(r"\b([A-Z])\.\s(?=[A-Z]\.)", r"\1<DOT> ", text)      # protect "P. B. Medawar"
    text = re.sub(r"\b([A-Z])\.\s(?=[A-Z][a-z])", r"\1<DOT> ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.replace("<DOT>", ".") for p in parts if p.strip()]


def _hard_wrap(s):
    if len(s) <= MAX_LINE:
        return [s]
    out = []
    while len(s) > MAX_LINE:
        w = s[:MAX_LINE]
        cut = max(w.rfind("; "), w.rfind(", "), w.rfind(" and "), w.rfind(" but "),
                  w.rfind(" which "), w.rfind(" because "))
        if cut < 60:
            cut = w.rfind(" ")
        out.append(s[:cut + 1].strip().rstrip(",;"))
        s = s[cut + 1:].strip()
    if s:
        out.append(s)
    return out


def to_kokoro_lines(raw):
    """raw text -> string with one normalized sentence per line, blank lines between paragraphs."""
    out = []
    for block in re.split(r"\n\s*\n", raw):
        block = block.strip()
        if not block:
            continue
        if _is_heading(block):
            out.append(block.title().replace("'S", "'s"))
            out.append("")
            continue
        joined = " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
        for sent in _split_sentences(normalize(joined)):
            out.extend(p for p in _hard_wrap(sent) if p)
        out.append("")
    return "\n".join(out).strip() + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python textprep.py in.txt out.txt")
    open(sys.argv[2], "w").write(to_kokoro_lines(open(sys.argv[1]).read()))
    n = sum(1 for l in open(sys.argv[2]) if l.strip())
    print(f"wrote {sys.argv[2]}  ({n} chunks)")
