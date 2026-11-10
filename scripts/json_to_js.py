#!/usr/bin/env python3
"""
bible_json_to_plugin_js.py
---------------------------------------------------------
Converts a Bible translation in Bible-SuperSearch JSON format
(https://www.biblesupersearch.com/bible-downloads/) to the
bible_data JS format that the obs-bible-plugin expects (assets/bibles/<name>/<name>.js).

FOR PRIVATE USE ONLY. Always check the "copyright_statement" in the
metadata of the respective JSON file before using.

Expected input format (Bible SuperSearch JSON):
{
  "metadata": { "name": "...", "shortname": "...", "copyright_statement": "...", ... },
  "verses": [
    {"book_name": "Genesis", "book": 1, "chapter": 1, "verse": 1, "text": "..."},
    ...
  ]
}

Generated output format (plugin-compatible):
var bible_data = [
  {"ari": "0:1:1", "name": "Genesis 1:1", "verse": "..."},
  ...
]

Usage:
    python3 json_to_js.py in/input.json out/output.js

Optional parameters:
    --strip-pilcrow     Removes leading "¶ " paragraph markers from verse text
    --strip-html        Removes simple HTML tags like <em>, <span ...> from verse text
    --indent N          Indentation in JS output (default: 2, 0 = compact/single line)

Expected number of books: 66 (Protestant canon, Genesis..Revelation).
Expected number of verses: 31102 (standard for most translations; may vary slightly
in some translations, the script only warns but does not abort).
"""

import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED_BOOK_COUNT = 66
EXPECTED_VERSE_COUNT_HINT = 31102  # just a hint value, not a hard requirement


def strip_pilcrow(text: str) -> str:
    return re.sub(r"^\s*¶\s*", "", text)


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def load_source(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if "verses" not in data:
        sys.exit(f"Error: '{path}' does not contain a 'verses' field. "
                  f"Is this really a Bible-SuperSearch JSON file?")
    return data


def convert(data: dict, strip_pilcrow_marks: bool, strip_html_tags: bool):
    verses_out = []
    books_seen = set()
    seen_ari = set()
    duplicates = 0

    for v in data["verses"]:
        try:
            book_num = int(v["book"])
            chapter = int(v["chapter"])
            verse_num = int(v["verse"])
            book_name = v["book_name"].strip()
            text = v["text"]
        except (KeyError, ValueError, TypeError) as e:
            sys.exit(f"Error: unexpected verse object {v!r} ({e})")

        if strip_pilcrow_marks:
            text = strip_pilcrow(text)
        if strip_html_tags:
            text = strip_html(text)
        text = text.strip()

        book_idx = book_num - 1  # Plugin expects 0-based book index (Genesis = 0)
        ari = f"{book_idx}:{chapter}:{verse_num}"
        name = f"{book_name} {chapter}:{verse_num}"

        if ari in seen_ari:
            duplicates += 1
            continue
        seen_ari.add(ari)
        books_seen.add(book_num)

        verses_out.append({"ari": ari, "name": name, "verse": text})

    return verses_out, books_seen, duplicates


def write_js(verses_out, out_path: Path, indent: int):
    with out_path.open("w", encoding="utf-8") as f:
        f.write("var bible_data = [\n")
        for i, v in enumerate(verses_out):
            comma = "," if i < len(verses_out) - 1 else ""
            if indent > 0:
                pad = " " * indent
                f.write(f"{pad}{{\n")
                f.write(f'{pad}  "ari": {json.dumps(v["ari"], ensure_ascii=False)},\n')
                f.write(f'{pad}  "name": {json.dumps(v["name"], ensure_ascii=False)},\n')
                f.write(f'{pad}  "verse": {json.dumps(v["verse"], ensure_ascii=False)}\n')
                f.write(f"{pad}}}{comma}\n")
            else:
                obj = json.dumps(v, ensure_ascii=False)
                f.write(f"  {obj}{comma}\n")
        f.write("]\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="Path to Bible-SuperSearch JSON file")
    parser.add_argument("output", type=Path, help="Path to the .js file to be created")
    parser.add_argument("--strip-pilcrow", action="store_true", help="Remove leading ¶ paragraph markers")
    parser.add_argument("--strip-html", action="store_true", help="Remove HTML tags from verse text")
    parser.add_argument("--indent", type=int, default=2, help="Indentation (0 = compact)")
    args = parser.parse_args()

    data = load_source(args.input)
    meta = data.get("metadata", {})

    print(f"Translation : {meta.get('name', '(unknown)')}")
    print(f"Short name  : {meta.get('shortname', '(unknown)')}")
    print(f"Language    : {meta.get('lang_short', '(unknown)')}")
    copyright_note = meta.get("copyright_statement")
    if copyright_note:
        print(f"Copyright   : {copyright_note}")
    print()

    verses_out, books_seen, duplicates = convert(
        data, args.strip_pilcrow, args.strip_html
    )

    write_js(verses_out, args.output, args.indent)

    print(f"Verses written    : {len(verses_out)}")
    print(f"Books detected    : {len(books_seen)} (expected: {EXPECTED_BOOK_COUNT})")
    if duplicates:
        print(f"WARNING: {duplicates} duplicate ari entries skipped.")
    if len(books_seen) != EXPECTED_BOOK_COUNT:
        print(f"WARNING: Expected {EXPECTED_BOOK_COUNT} books, found {len(books_seen)}.")
    if abs(len(verses_out) - EXPECTED_VERSE_COUNT_HINT) > 500:
        print(f"Note: Verse count ({len(verses_out)}) differs significantly from "
              f"the typical reference value ({EXPECTED_VERSE_COUNT_HINT}). Some "
              f"translations (e.g., with/without apocrypha) may vary normally - verify briefly.")
    print(f"\nDone: {args.output}")


if __name__ == "__main__":
    main()