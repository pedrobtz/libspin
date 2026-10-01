#!/usr/bin/env python3
"""Generate the per-translation-unit reset functions for Spin's globals.

    tools/globals.py            regenerate Src/spin_reset_*.inc, Src/spin_reset.inc,
                                tools/globals.txt
    tools/globals.py --check    regenerate into a scratch dir and fail if anything
                                differs from what is committed (CI runs this)

Why generated: a fresh process was the only thing that ever reset Spin's ~320
mutable globals. The library must do it on every spin_main_once(), and a
hand-written list would silently rot the first time upstream adds a variable.
So the list comes from the compiler: every source is built at -O0 (so clang
does not split arrays into `EPT.0`, `EPT.1`) and `nm` reports which symbols sit
in a writable section. Function-local statics show up as dotted names and are
rejected: they have to be hoisted to file scope first (see the Stage 2 commits).

How each symbol is reset: a zero-initialised symbol (bss/common) gets memset;
an initialised one (data) gets a copy of a `static const __typeof__(x)` holding
the initialiser text, taken verbatim from the declaration in the source, so the
type never has to be parsed. Declarations inside `#if` blocks reproduce the same
guards. The reset for TU foo lives in Src/spin_reset_foo.inc, included at the
end of foo.c (or spin.y, for the parser) so that it can see the file's statics.
Those include lines are the only hand-made part and this tool checks they exist.

Needs a C compiler ($CC, default cc) and nm. Maintainer-side only: nothing here
runs when the library is built.
"""
import os, re, subprocess, sys, tempfile, filecmp, platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Src")
CC = os.environ.get("CC", "cc")
CFLAGS = ["-std=gnu99", "-O0", "-DNXT"]
NOT_LIBRARY = {"spin_cli.c", "spin_lib.c"}          # spin_lib's own state must survive a reset
# Not variables: our own init constants (if nm ever shows them), and the
# assembler's section-start temporaries that newer Apple toolchains emit as
# non-external data symbols (ltmp0, ltmp1, ...).
GENERATED = re.compile(r"^spin_init_|^ltmp\d+$")

# ---------------------------------------------------------------- symbols --

def translation_units():
    """(tu_name, compile_source, declaration_source, include_target)"""
    tus = []
    for f in sorted(os.listdir(SRC)):
        if f.endswith(".c") and f not in NOT_LIBRARY and f != "y.tab.c" and not f.startswith("spin_reset"):
            tus.append((f[:-2], f, f, f))
    # the parser: compiled from y.tab.c, declared in y.tab.c (it contains spin.y's
    # prologue verbatim), but the include line lives in spin.y so regeneration keeps it
    tus.append(("spin", "y.tab.c", "y.tab.c", "spin.y"))
    return tus

def writable_symbols(obj):
    """{name: 'zero'|'data'} for symbols in writable sections."""
    out = {}
    if platform.system() == "Darwin":
        txt = subprocess.check_output(["nm", "-m", obj], text=True)
        for line in txt.splitlines():
            # "(__DATA,__data) external _x", "(__DATA,__bss) non-external _y", and
            # uninitialised externs as "(common) (alignment 2^3) external _z"
            m = re.search(r"\((?:__DATA,__(data|bss|common)|(common))\)(?:\s+\(alignment[^)]*\))?\s+(?:non-)?external\s+_?(\S+)$", line)
            if m:
                out[m.group(3)] = "data" if m.group(1) == "data" else "zero"
    else:
        txt = subprocess.check_output(["nm", obj], text=True)
        for line in txt.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[1] in "BbDdCc":
                out[parts[2]] = "data" if parts[1] in "Dd" else "zero"
    return {k: v for k, v in out.items() if not GENERATED.match(k)}

# ----------------------------------------------------------- declarations --

def strip_comments(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("/*", i):
            j = text.index("*/", i) + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j])); i = j
        elif text.startswith("//", i):
            j = text.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1]); i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)

def guard_stack_by_line(text):
    """For each line index, the list of #if guards active there (as emitted text).
    Preprocessor lines themselves are blanked in the returned text."""
    lines = text.split("\n")
    stack, per_line, out_lines = [], [], []
    def dead():   # inside '#if 0' (not its #else), or the #else of '#if 1'?
        return any(k == "if" and ((e == "0" and not neg) or (e == "1" and neg))
                   for k, e, neg in stack)
    continued = False      # previous line was a directive ending in a backslash
    for ln in lines:
        s = ln.strip()
        if continued:
            out_lines.append(""); per_line.append([tuple(x) for x in stack])
            continued = s.endswith("\\")
            continue
        if s.startswith("#"):
            continued = s.endswith("\\")
            d = s[1:].strip()
            m = re.match(r"(ifdef|ifndef|if|elif|else|endif)\b\s*(.*)", d)
            if m:
                kind, expr = m.group(1), m.group(2).strip()
                if kind in ("ifdef", "ifndef", "if"):
                    stack.append([kind, expr, False])
                elif kind == "else":
                    stack[-1][2] = True
                elif kind == "elif":
                    stack[-1] = ["if", expr, False]     # approximate: treat as its own branch
                elif kind == "endif":
                    stack.pop()
                # Conditionals stay in the text: pangen1.h's code tables switch
                # elements on #ifdef inside the initializer, and the copied
                # initializer must keep them or it gets both branches.
                out_lines.append(ln)
            else:
                out_lines.append("")                      # includes, defines: blank
        else:
            out_lines.append("" if dead() else ln)        # '#if 0' bodies are comments
        per_line.append([tuple(x) for x in stack])
    return "\n".join(out_lines), per_line

def emit_guards(stack):
    opens = []
    for kind, expr, negated in stack:
        if kind == "ifdef":  opens.append(("#ifndef %s" if negated else "#ifdef %s") % expr)
        elif kind == "ifndef": opens.append(("#ifdef %s" if negated else "#ifndef %s") % expr)
        else: opens.append(("#if !(%s)" if negated else "#if %s") % expr)
    return opens, ["#endif"] * len(opens)

def top_level_statements(text):
    """Yield (start_offset, statement_text) for file-scope declarations, skipping
    function bodies."""
    depth = 0; start = 0; i = 0; n = len(text)
    saw_paren_just_before_brace = False
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1; continue
        if c == "{":
            stmt_so_far = text[start:i]
            if depth == 0 and "=" not in re.sub(r"\([^()]*\)", "", stmt_so_far) and stmt_so_far.rstrip().endswith(")"):
                # function definition: skip the body
                d = 1; j = i + 1
                while j < n and d:
                    cj = text[j]
                    if cj in "\"'":
                        k = j + 1
                        while k < n and text[k] != cj:
                            k += 2 if text[k] == "\\" else 1
                        j = k + 1; continue
                    if cj == "{": d += 1
                    elif cj == "}": d -= 1
                    j += 1
                i = j; start = i; continue
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == ";" and depth == 0:
            stmt = text[start:i]
            if stmt.strip():
                yield start, stmt
            start = i + 1
        i += 1

def split_top_level(s, sep):
    parts, depth, cur = [], 0, []
    i = 0
    while i < len(s):
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < len(s) and s[j] != c:
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1]); i = j + 1; continue
        if c in "([{": depth += 1
        elif c in ")]}": depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts

def declarations(text):
    """{name: (initializer_text_or_None, guard_stack)} for file-scope variables."""
    text = strip_comments(text)
    text, guards = guard_stack_by_line(text)
    line_of = lambda off: text.count("\n", 0, off)
    decls = {}
    for off, stmt in top_level_statements(text):
        s = stmt.strip()
        if not s or s.startswith(("typedef", "extern", "struct ", "union ", "enum ")) and "=" not in s and not re.search(r"\}\s*\w+\s*(\[|=|$)", s):
            # typedefs, externs, and bare struct/union/enum definitions declare no variable
            if s.startswith(("typedef", "extern")) or ("=" not in s and re.match(r"(struct|union|enum)\b[^{]*\{", s) and re.search(r"\}\s*$", s)):
                continue
        for part in split_top_level(stmt, ","):
            p = part.strip()
            if not p:
                continue
            # conditionals *before* the declaration were kept in the text; drop
            # those leading lines only (ones inside an initializer must stay)
            while re.match(r"\s*#", p):
                p = p.split("\n", 1)[1] if "\n" in p else ""
            p = p.strip()
            if not p:
                continue
            eq = split_top_level(p, "=")          # '=' inside a literal does not count
            if len(eq) > 1:
                lhs, init = eq[0].strip(), "=".join(eq[1:]).strip()
            else:
                lhs, init = p, None
            # a function prototype has '(' right after the declarator's name
            name_m = re.search(r"([A-Za-z_]\w*)\s*((\[[^\]]*\])*)\s*$", lhs)
            if not name_m:
                continue
            name = name_m.group(1)
            before = lhs[:name_m.start(1)].rstrip()
            if before.endswith("(") or re.search(r"\)\s*$", lhs) or "(" in lhs and ")" in lhs and "=" not in p and not re.search(r"\(\s*\*", lhs):
                continue
            if name in ("static", "const", "int", "char", "void", "long", "short", "unsigned", "signed", "double", "float"):
                continue
            # the guard that applies is the one at the declaration itself; the
            # statement text starts right after the previous ';' and may begin
            # with the '#ifndef PC' line that guards it
            decls[name] = (init, guards[line_of(off + len(stmt))])
    return decls

# ------------------------------------------------------------------ emit --

def reset_source(tu, syms, decls):
    lines = ["/* Generated by tools/globals.py; do not edit. Re-initialises every",
             " * mutable file-scope variable of %s to the value it has in a fresh" % tu,
             " * process. Included at the end of the translation unit. */",
             "", "void", "spin_reset_%s(void)" % tu, "{"]
    missing = []
    for name in sorted(syms):
        kind = syms[name]
        if name not in decls:
            missing.append(name); continue
        init, stack = decls[name]
        opens, closes = emit_guards(stack)
        lines += opens
        if kind == "zero" or init is None:
            if kind == "data":
                missing.append(name + " (in .data but no initializer found)"); continue
            lines.append("\tmemset(&%s, 0, sizeof %s);" % (name, name))
        else:
            lines.append("\t{\tstatic const __typeof__(%s) spin_init_%s = %s;" % (name, name, init))
            lines.append("\t\tmemcpy(&%s, &spin_init_%s, sizeof %s);" % (name, name, name))
            lines.append("\t}")
        lines += closes
    lines += ["}", ""]
    return "\n".join(lines), missing

def with_quoted_includes(path, seen=None):
    """The file and, recursively, every #include "x" it names that exists in Src/.
    Headers are parsed with the same declaration scanner; their externs are
    skipped there, their definitions (pangen1.h's code tables) are found."""
    seen = seen if seen is not None else []
    if path in seen or not os.path.exists(path):
        return seen
    seen.append(path)
    with open(path) as fh:
        for m in re.finditer(r'^\s*#\s*include\s+"([^"]+)"', fh.read(), re.M):
            if not m.group(1).startswith("spin_reset"):
                with_quoted_includes(os.path.join(SRC, m.group(1)), seen)
    return seen

def main():
    check = "--check" in sys.argv
    outdir = tempfile.mkdtemp(prefix="libspin-globals.") if check else SRC
    objdir = tempfile.mkdtemp(prefix="libspin-o0.")
    tus = translation_units()
    # The discovery build runs in a scratch copy of Src/ where every
    # spin_reset_*.inc is empty: the sources include those files, and the
    # symbol list must not depend on the previous generation's output
    # (or on its existence, the first time).
    import shutil
    scratch = os.path.join(objdir, "src"); os.mkdir(scratch)
    for f in os.listdir(SRC):
        if not f.startswith("spin_reset") and os.path.isfile(os.path.join(SRC, f)):
            shutil.copy(os.path.join(SRC, f), scratch)
    for tu, _, _, _ in tus:
        open(os.path.join(scratch, "spin_reset_%s.inc" % tu), "w").close()
    table, all_names, problems = [], [], []
    for tu, csrc, dsrc, inc_target in tus:
        obj = os.path.join(objdir, tu + ".o")
        subprocess.check_call([CC] + CFLAGS + ["-I", scratch, "-c", os.path.join(scratch, csrc), "-o", obj])
        syms = writable_symbols(obj)
        dotted = [s for s in syms if "." in s]
        if dotted:
            problems.append("%s: function-local statics must be hoisted to file scope: %s" % (tu, " ".join(sorted(dotted))))
            continue
        decls = {}
        for path in with_quoted_includes(os.path.join(SRC, dsrc)):
            with open(path) as fh:
                decls.update(declarations(fh.read()))
        text, missing = reset_source(tu, syms, decls)
        if missing:
            problems.append("%s: no file-scope declaration found for: %s" % (tu, ", ".join(missing)))
        inc_line = '#include "spin_reset_%s.inc"' % tu
        with open(os.path.join(SRC, inc_target)) as fh:
            if inc_line not in fh.read():
                problems.append("%s: %s must contain the line %s" % (tu, inc_target, inc_line))
        with open(os.path.join(outdir, "spin_reset_%s.inc" % tu), "w") as fh:
            fh.write(text)
        all_names.append(tu)
        table += ["%s %s %s" % (tu, syms[n], n) for n in sorted(syms)]
    if problems:
        print("\n".join(problems), file=sys.stderr); sys.exit(2)
    with open(os.path.join(outdir, "spin_reset.inc"), "w") as fh:
        fh.write("/* Generated by tools/globals.py; do not edit. Included by spin_lib.c. */\n\n")
        fh.write("".join("void spin_reset_%s(void);\n" % t for t in all_names))
        fh.write("\nstatic void\nreset_all_globals(void)\n{\n")
        fh.write("".join("\tspin_reset_%s();\n" % t for t in all_names))
        fh.write("}\n")
    tbl = os.path.join(outdir if check else os.path.join(ROOT, "tools"), "globals.txt")
    with open(tbl, "w") as fh:
        fh.write("# tu section symbol -- generated by tools/globals.py from an -O0 build; %d symbols\n" % len(table))
        fh.write("\n".join(table) + "\n")
    if check:
        bad = []
        for f in os.listdir(outdir):
            ref = os.path.join(ROOT, "tools" if f == "globals.txt" else "Src", f)
            if not os.path.exists(ref) or not filecmp.cmp(os.path.join(outdir, f), ref, shallow=False):
                bad.append(f)
        if bad:
            print("globals: out of date, run tools/globals.py: %s" % " ".join(sorted(bad)), file=sys.stderr); sys.exit(1)
        print("globals: %d symbols in %d translation units, up to date" % (len(table), len(all_names)))
    else:
        print("globals: wrote %d resets for %d symbols" % (len(all_names), len(table)))

if __name__ == "__main__":
    main()
