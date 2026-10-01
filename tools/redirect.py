#!/usr/bin/env python3
"""Route Spin's console I/O through library-owned streams.

    tools/redirect.py           rewrite Src/*.c and Src/spin.y in place
    tools/redirect.py --check   exit 1 if any library source still names a
                                standard stream or calls printf (CI)

Upstream writes to stdout/stderr and reads stdin directly, in ~2,900 calls,
and many helpers take a FILE * that callers pass `stdout` into. So the
rewrite is of the stream *names*, not of the calls:

    stdout      -> spin_out        printf(      -> spin_printf(
    stderr      -> spin_err        getchar()    -> getc(spin_in)
    stdin       -> spin_in

spin_out/spin_err/spin_in are FILE * owned by spin_lib.c; the CLI points
them at the real streams, an embedder at whatever it likes. fflush(stdout),
comment(stdout, ...), yyin = stdin and the rest follow automatically.

Replacement is token-aware: nothing inside a string or character literal
or a comment is touched, which matters because pangen*.c emit C source
containing the words printf and stdout as text. Idempotent, so it is
re-run after every upstream merge; the diff it produces is the review.
Generated files (y.tab.c, spin_reset_*.inc) and spin_lib.c itself, which
has to name the real streams, are left alone.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Src")
SKIP = {"spin_lib.c", "spin_cli.c", "y.tab.c"}

RULES = [
    (re.compile(r"\bstdout\b"), "spin_out"),
    (re.compile(r"\bstderr\b"), "spin_err"),
    (re.compile(r"\bstdin\b"), "spin_in"),
    (re.compile(r"(?<![\w.>])printf\s*\("), "spin_printf("),
    (re.compile(r"\bgetchar\s*\(\s*\)"), "getc(spin_in)"),
]
FORBIDDEN = re.compile(r"\b(stdout|stderr|stdin|getchar)\b|(?<![\w.>])printf\s*\(")

def segments(text):
    """Yield (is_code, chunk): code chunks are rewritable, literals and comments are not."""
    i, n, start = 0, len(text), 0
    while i < n:
        c = text[i]
        if text.startswith("/*", i):
            j = text.find("*/", i + 2); j = n if j < 0 else j + 2
            yield True, text[start:i]; yield False, text[i:j]; i = start = j
        elif text.startswith("//", i):
            j = text.find("\n", i); j = n if j < 0 else j
            yield True, text[start:i]; yield False, text[i:j]; i = start = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            yield True, text[start:i]; yield False, text[i:j]; i = start = j
        else:
            i += 1
    yield True, text[start:]

def rewrite(text):
    out = []
    for is_code, chunk in segments(text):
        if is_code:
            for rx, rep in RULES:
                chunk = rx.sub(rep, chunk)
        out.append(chunk)
    return "".join(out)

def offenders(text):
    hits = []
    for is_code, chunk in segments(text):
        if is_code:
            hits += [m.group(0) for m in FORBIDDEN.finditer(chunk)]
    return hits

def sources():
    for f in sorted(os.listdir(SRC)):
        if (f.endswith(".c") or f == "spin.y") and f not in SKIP and not f.startswith("spin_reset"):
            yield f

def main():
    check = "--check" in sys.argv
    bad, changed = [], []
    for f in sources():
        path = os.path.join(SRC, f)
        with open(path) as fh:
            text = fh.read()
        if check:
            hits = offenders(text)
            if hits:
                bad.append("%s: %s" % (f, " ".join(sorted(set(hits)))))
        else:
            new = rewrite(text)
            if new != text:
                with open(path, "w") as fh:
                    fh.write(new)
                changed.append(f)
    if check:
        if bad:
            print("redirect: library code still touches a console stream; run tools/redirect.py:\n  " + "\n  ".join(bad), file=sys.stderr)
            sys.exit(1)
        print("redirect: no console streams named in library code")
    else:
        print("redirect: rewrote %d files%s" % (len(changed), ": " + " ".join(changed) if changed else ""))

if __name__ == "__main__":
    main()
