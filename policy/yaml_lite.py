"""Minimal YAML-subset parser (pure stdlib).

Supports only the constructs used by policy/policy.yaml:
  - comments (# ...)
  - nested mappings via 2-space indentation
  - sequences ("- item" and "- key: value")
  - scalars: strings (plain, single/double quoted), ints, floats, bools, null

This is intentionally NOT a general YAML parser. If policy.yaml grows
constructs beyond this subset, the loader raises YamlLiteError naming the
offending line so the file can be simplified or a real parser adopted.
"""

import re


class YamlLiteError(Exception):
    pass


def _scalar(text):
    t = text.strip()
    if t in ("", "~", "null", "Null", "NULL"):
        return None
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
        inner = t[1:-1]
        if t[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n")
        return inner
    low = t.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"[+-]?\d+", t):
        return int(t)
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", t):
        return float(t)
    if re.fullmatch(r"[+-]?\d+[eE][+-]?\d+", t):
        return float(t)
    return t


def _strip_comment(line):
    in_s = in_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d and i > 0 and line[i - 1] in (" ", "\t"):
            return line[:i]
    return line


def loads(text):
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if "\t" in line:
            raise YamlLiteError(f"tabs not allowed: {raw!r}")
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise YamlLiteError(f"indent must be a multiple of 2: {raw!r}")
        lines.append((indent, line.strip()))

    i = 0
    n = len(lines)

    def parse_block(indent):
        nonlocal i
        if i >= n or lines[i][0] != indent:
            raise YamlLiteError("empty or misaligned block")
        if lines[i][1].startswith("- ") or lines[i][1] == "-":
            seq = []
            while i < n and lines[i][0] == indent:
                content = lines[i][1]
                if not content.startswith("- "):
                    break
                item = content[2:].strip()
                i += 1
                if ": " in item or item.endswith(":"):
                    d = {}
                    k, _, v = item.partition(":")
                    k = k.strip()
                    v = v.strip()
                    d[k] = _scalar(v) if v else None
                    while i < n and lines[i][0] > indent:
                        _parse_mapping_into(d, lines[i][0])
                    seq.append(d)
                else:
                    seq.append(_scalar(item))
            return seq
        d = {}
        _parse_mapping_into(d, indent)
        return d

    def _parse_mapping_into(d, indent):
        nonlocal i
        while i < n and lines[i][0] == indent:
            content = lines[i][1]
            if content.startswith("- "):
                raise YamlLiteError(f"sequence item inside mapping block: {content!r}")
            if ": " not in content and not content.endswith(":"):
                raise YamlLiteError(f"cannot parse line: {content!r}")
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            i += 1
            if val == "" and i < n and lines[i][0] > indent:
                d[key] = parse_block(lines[i][0])
            else:
                d[key] = _scalar(val)

    if not lines:
        return {}
    return parse_block(lines[0][0])


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read())
