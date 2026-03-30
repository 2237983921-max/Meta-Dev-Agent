#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
import sys
from collections import Counter
from typing import Iterable, List, Dict, Tuple, Optional

WORD_PATTERN = re.compile(r"\w+", flags=re.UNICODE)

def tokenize(text: str) -> List[str]:
    """
    Split text into words using a Unicode-aware pattern.
    Lowercase for case-insensitive counting.
    """
    if not text:
        return []
    return [w.lower() for w in WORD_PATTERN.findall(text)]

def load_stopwords(path: Optional[str]) -> Optional[set]:
    if not path:
        return None
    sw = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sw.add(line.lower())
    return sw

def count_words(words: Iterable[str], stopwords: Optional[set] = None) -> Dict[str, int]:
    c = Counter()
    if stopwords:
        for w in words:
            if w not in stopwords:
                c[w] += 1
    else:
        c.update(words)
    return dict(c)

def top_n(counts: Dict[str, int], n: int) -> List[Tuple[str, int]]:
    if n <= 0:
        return []
    # sort by (-count, word) for deterministic ties
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]

def analyze_text(text: str, top: int = 10, stopwords: Optional[set] = None) -> List[Dict[str, int]]:
    words = tokenize(text)
    counts = count_words(words, stopwords=stopwords)
    result = [{"word": w, "count": c} for w, c in top_n(counts, top)]
    return result

def _read_text_from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Word frequency counter")
    parser.add_argument("--file", "-f", help="Input file path. If omitted, read from STDIN.")
    parser.add_argument("--top", "-n", type=int, default=10, help="Top N words (default: 10)")
    parser.add_argument("--stopwords", "-s", help="Stopwords file (UTF-8, one per line, supports # comments)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        if args.file:
            text = _read_text_from_file(args.file)
        else:
            text = sys.stdin.read()
    except FileNotFoundError:
        sys.stderr.write(f"ERROR: File not found: {args.file}\n")
        return 2
    except UnicodeDecodeError:
        sys.stderr.write(f"ERROR: Failed to decode input as UTF-8.\n")
        return 3
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 1

    try:
        stopwords = load_stopwords(args.stopwords)
        result = analyze_text(text, top=args.top, stopwords=stopwords)
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 1

if __name__ == "__main__":
    sys.exit(cli_main())
