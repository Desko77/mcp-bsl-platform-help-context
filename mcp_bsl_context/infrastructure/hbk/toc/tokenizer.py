"""Tokenizer for 1C bracket file format used in TOC."""

from __future__ import annotations

BOM = "\ufeff"


def tokenize(content: str) -> list[str]:
    """Tokenize a bracket-file format string into a list of tokens.

    The bracket format uses:
    - { } as block delimiters
    - Quoted strings "..."
    - Numbers and identifiers as plain tokens
    - Commas as separators (ignored)
    """
    tokens: list[str] = []
    current: list[str] = []
    in_string = False
    i = 0
    length = len(content)

    while i < length:
        char = content[i]

        if char == BOM:
            i += 1
            continue

        if char == '"':
            if in_string:
                # Check for escaped quote ("")
                if i + 1 < length and content[i + 1] == '"':
                    current.append('"')
                    i += 2
                    continue
                else:
                    current.append(char)
                    tokens.append("".join(current))
                    current.clear()
                    in_string = False
            else:
                if current:
                    token = "".join(current).strip()
                    if token:
                        tokens.append(token)
                    current.clear()
                current.append(char)
                in_string = True
        elif in_string:
            current.append(char)
        elif char.isspace():
            if current:
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current.clear()
        elif char in "{}":
            if current:
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current.clear()
            tokens.append(char)
        elif char == ",":
            if current:
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current.clear()
        else:
            current.append(char)

        i += 1

    if current:
        token = "".join(current).strip()
        if token:
            tokens.append(token)

    return tokens
