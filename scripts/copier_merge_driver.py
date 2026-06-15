#!/usr/bin/env python3
"""
copier_merge.py - a git merge driver that resolves "managed blocks" during
copier updates, so template-owned regions update cleanly while the rest of a
file stays under human control.

CONTRACT
--------
A file may contain one or more *managed blocks*, delimited by language-agnostic
markers built around the tokens ``copier:begin`` / ``copier:end``. Write them
using your language's own comment syntax - only the token is matched, not the
comment characters around it:

    # copier:begin:settings            <- Python / YAML / TOML / shell / CUE(#)
    generated...
    # copier:end:settings

    // copier:begin:imports            <- CUE / Go / Rust / JS
    generated...
    // copier:end:imports

    <!-- copier:begin:head -->         <- HTML / XML / Markdown
    generated...
    <!-- copier:end:head -->

The optional id after the token (``:settings``) lets blocks be matched across
versions even if they move. Without an id, blocks are matched by position.

BEHAVIOUR
---------
During a copier update (gated by the COPIER_MERGE env var) the driver:
  * takes each managed block from the TEMPLATE side (3-way aware: if the human
    never touched the block it takes the template's update; if the template did
    not change the block it keeps the human's version), and
  * keeps everything OUTSIDE managed blocks from the LOCAL (human) side.
=> partially-generated files never produce a conflict.

Outside a copier update (COPIER_MERGE unset) it transparently reproduces git's
default 3-way text merge, so ordinary branch merges / rebases are unaffected.

git invokes the driver with the placeholders configured in --install:
    %O = base (ancestor)   %A = ours    %B = theirs   %P = path   %L = marker size
The merged result must be left in the %A path; exit 0 = clean, non-zero = the
file is left with conflicts for the user to resolve.

ENV KNOBS
---------
  COPIER_MERGE=1                 enable managed-block handling (set when running copier)
  COPIER_MERGE_LOCAL=A|B         which git side is the human's project (default A=ours)
  COPIER_MERGE_BLOCK_CONFLICT=   theirs (default) | ours | mark
                                 what to do if a block was edited on BOTH sides
  COPIER_MERGE_BEGIN / _END      override the marker tokens
  COPIER_MERGE_DEBUG=1           log decisions to stderr

INSTALL (per repo, scriptable across hosts)
-------------------------------------------
    python3 copier_merge.py --install            # writes the driver into .git/config
    echo '*.cue merge=copier-block' >> .gitattributes
    echo '*.py  merge=copier-block' >> .gitattributes

Then update with:  COPIER_MERGE=1 copier update
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Markers
# --------------------------------------------------------------------------- #
BEGIN_TOKEN = os.environ.get("COPIER_MERGE_BEGIN", "copier:begin")
END_TOKEN = os.environ.get("COPIER_MERGE_END", "copier:end")


def _token_re(token: str) -> re.Pattern:
    # Match the token anywhere on the line; an optional id may follow after
    # ':', '=' or whitespace. Comment characters around it are ignored.
    return re.compile(re.escape(token) + r"(?:[:=\s]+([\w.\-/]+))?")


BEGIN_RE = _token_re(BEGIN_TOKEN)
END_RE = _token_re(END_TOKEN)

DEBUG = bool(os.environ.get("COPIER_MERGE_DEBUG"))


def log(*a) -> None:
    if DEBUG:
        print("[copier-merge]", *a, file=sys.stderr)


# --------------------------------------------------------------------------- #
# Byte-safe IO (round-trips arbitrary content and line endings exactly)
# --------------------------------------------------------------------------- #
def read_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read().splitlines(keepends=True)


def write_lines(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write("".join(lines))


# --------------------------------------------------------------------------- #
# Parsing into segments / blocks
# --------------------------------------------------------------------------- #
class Block:
    __slots__ = ("id", "index", "lines")

    def __init__(self, id_: str | None, index: int, lines: list[str]):
        self.id = id_
        self.index = index  # positional order among blocks in this file
        self.lines = lines  # full block, INCLUDING its begin/end marker lines


def parse_segments(lines: list[str]):
    """Split a file into an ordered list of segments.

    Returns (segments, blocks) where segments is a list of
    ("free", list[str]) | ("block", Block), and blocks is the list[Block]
    for convenient lookup. A begin marker without a matching end is treated as
    ordinary free text, so malformed input can never corrupt the result.
    """
    segments: list = []
    blocks: list[Block] = []
    free: list[str] = []
    i, n, block_index = 0, len(lines), 0

    while i < n:
        if BEGIN_RE.search(lines[i]):
            m = BEGIN_RE.search(lines[i])
            j = i + 1
            while j < n and not END_RE.search(lines[j]):
                j += 1
            if j < n:  # found a matching end marker
                if free:
                    segments.append(("free", free))
                    free = []
                blk = Block(m.group(1), block_index, lines[i : j + 1])
                segments.append(("block", blk))
                blocks.append(blk)
                block_index += 1
                i = j + 1
                continue
            # no end marker -> not a real block; fall through as free text
        free.append(lines[i])
        i += 1

    if free:
        segments.append(("free", free))
    return segments, blocks


def index_by_id(blocks: list[Block]) -> dict[str, Block]:
    out: dict[str, Block] = {}
    for b in blocks:
        if b.id is not None:
            out.setdefault(b.id, b)
    return out


def find_counterpart(blk: Block, by_id: dict[str, Block], blocks: list[Block]):
    """Locate the same block in another version: by id, else by position."""
    if blk.id is not None:
        return by_id.get(blk.id)
    return blocks[blk.index] if blk.index < len(blocks) else None


# --------------------------------------------------------------------------- #
# Block-level 3-way resolution
# --------------------------------------------------------------------------- #
def _text(blk: Block | None) -> str | None:
    return "".join(blk.lines) if blk is not None else None


def _conflict_markers(local_lines, tmpl_lines, size: int) -> list[str]:
    lt, eq, gt = "<" * size, "=" * size, ">" * size

    def ensure_nl(seq):
        if seq and not seq[-1].endswith(("\n", "\r")):
            return seq + ["\n"]
        return seq

    return (
        [lt + " ours (local)\n"]
        + ensure_nl(list(local_lines))
        + [eq + "\n"]
        + ensure_nl(list(tmpl_lines))
        + [gt + " theirs (template)\n"]
    )


def resolve_block(local_blk, base_blk, tmpl_blk, policy, size):
    """Decide the contents of one managed block. Returns (lines, conflict)."""
    L, B, T = _text(local_blk), _text(base_blk), _text(tmpl_blk)

    if T is None:
        log(f"block {local_blk.id or local_blk.index}: template dropped it -> keep local")
        return local_blk.lines, False
    if L == T:
        return tmpl_blk.lines, False
    if B is not None and L == B:
        log(f"block {local_blk.id or local_blk.index}: human untouched -> take template")
        return tmpl_blk.lines, False
    if B is not None and T == B:
        log(f"block {local_blk.id or local_blk.index}: template untouched -> keep local")
        return local_blk.lines, False

    # Block diverged on both sides (human edited inside a template-owned block).
    log(f"block {local_blk.id or local_blk.index}: both changed -> policy={policy}")
    if policy == "ours":
        return local_blk.lines, True
    if policy == "mark":
        return _conflict_markers(local_blk.lines, tmpl_blk.lines, size), True
    return tmpl_blk.lines, True  # default: template owns the block


# --------------------------------------------------------------------------- #
# Merge entry points
# --------------------------------------------------------------------------- #
def git_merge_file(base_path, ours_path, theirs_path, size) -> int:
    """Reproduce git's default text merge (result written into ours_path)."""
    res = subprocess.run(
        ["git", "merge-file", "--marker-size", str(size),
         ours_path, base_path, theirs_path],
        capture_output=True, text=True,
    )
    return res.returncode  # >0 = number of remaining conflicts, <0 = error


def merge(base_path, ours_path, theirs_path, size) -> int:
    local_is_a = os.environ.get("COPIER_MERGE_LOCAL", "A").upper() != "B"
    local_path = ours_path if local_is_a else theirs_path
    tmpl_path = theirs_path if local_is_a else ours_path

    local_segs, local_blocks = parse_segments(read_lines(local_path))
    _, base_blocks = parse_segments(read_lines(base_path))
    _, tmpl_blocks = parse_segments(read_lines(tmpl_path))

    if not local_blocks:
        # No managed blocks here -> behave exactly like git's default merge,
        # so the template can still update such files and surface real conflicts.
        return git_merge_file(base_path, ours_path, theirs_path, size)

    base_by_id = index_by_id(base_blocks)
    tmpl_by_id = index_by_id(tmpl_blocks)
    policy = os.environ.get("COPIER_MERGE_BLOCK_CONFLICT", "theirs").lower()

    out: list[str] = []
    conflicted = False
    for kind, payload in local_segs:
        if kind == "free":
            out.extend(payload)  # human owns everything outside blocks
        else:
            blk = payload
            tmpl_blk = find_counterpart(blk, tmpl_by_id, tmpl_blocks)
            base_blk = find_counterpart(blk, base_by_id, base_blocks)
            lines, conflict = resolve_block(blk, base_blk, tmpl_blk, policy, size)
            out.extend(lines)
            conflicted = conflicted or conflict

    write_lines(ours_path, out)  # git always reads the result from the %A path
    # Only report a conflict (non-zero) when we actually left markers in place.
    return 1 if (conflicted and policy == "mark") else 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def install(argv) -> int:
    name = "copier-block"
    if "--name" in argv:
        name = argv[argv.index("--name") + 1]
    script = str(Path(__file__).resolve())
    driver = f'python3 "{script}" %O %A %B %P %L'
    subprocess.run(["git", "config", f"merge.{name}.name",
                    "copier managed-block merge driver"], check=True)
    subprocess.run(["git", "config", f"merge.{name}.driver", driver], check=True)
    print(f"Installed merge driver '{name}' into .git/config.")
    print(f"Now map files to it in .gitattributes, e.g.:  *.cue merge={name}")
    return 0


def main(argv) -> int:
    if "--install" in argv:
        return install(argv)

    positional = [a for a in argv if not a.startswith("--")]
    if len(positional) < 3:
        print("usage: copier_merge.py %O %A %B [%P] [%L]   (or --install)",
              file=sys.stderr)
        return 2

    base, ours, theirs = positional[0], positional[1], positional[2]
    size = 7
    if len(positional) >= 5 and positional[4].isdigit():
        size = int(positional[4])

    # Only do special handling during a copier update; otherwise normal merges
    # must behave exactly as git would by default.
    if not os.environ.get("COPIER_MERGE"):
        return git_merge_file(base, ours, theirs, size)

    try:
        return merge(base, ours, theirs, size)
    except Exception as exc:  # never corrupt a file: degrade to a normal merge
        log("error, falling back to default merge:", repr(exc))
        return git_merge_file(base, ours, theirs, size)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))