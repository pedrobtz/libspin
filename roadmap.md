# libspin roadmap

Goal: turn Spin (nimble-code/Spin, the Promela model checker) from a command-line program into
an embeddable C library, `libspin`, with the original `spin` executable rebuilt as a thin wrapper
over it. The first consumer is the R package [zuspin](https://github.com/pedrobtz/zuspin), whose
own roadmap lives in that repo; stages here are ordered so that zuspin can start vendoring as
early as possible.

## What we are starting from

Facts established from upstream `master` at the seed commit (Spin 6.5.2, September 2025). Re-verify
after every upstream merge.

| Property | Value | Consequence |
| --- | --- | --- |
| License | BSD 3-Clause (Bell Labs provenance note in `Src/LICENSE`) | Keep the file verbatim; derived work stays BSD |
| Language | C, `-std=c99` builds clean with `cc` on macOS | No toolchain risk; C is also what R vendors most easily |
| Size | 41 files in `Src/`, ~26k lines of `.c`/`.y`, ~44k with headers | Mechanical transformations must be scripted, not hand-edited |
| Grammar | `spin.y`; `y.tab.c`/`y.tab.h` are **not** committed; makefile runs `yacc -v -d`, 6 reduce/reduce conflicts | Generated parser must be committed for consumers; pin one generator (bison) so the output is stable |
| Mutable globals | 362 data symbols across the objects (97 external, the rest `static`), heaviest in `pangen2.o` (59), `pangen1.o` (38), `main.o` (32), `spinlex.o` (31), `spin.o` (27, yacc's own) | A fresh process was the only reset. See Stage 3 |
| Function-local `static` | 16 across 9 files | Must be found by grep and reset by hand; `nm` cannot tell them from file-scope statics |
| Allocation | Everything goes through `emalloc()` (one `malloc` in `main.c`) and `tl_emalloc()` (`tl_mem.c`); one `free()` in `spin.y`. Nothing is ever freed | An arena behind `emalloc` gives per-call cleanup almost for free. See Stage 1 |
| Termination | `exit()` 9 times, `alldone()` from 10 files, `fatal()`/`non_fatal()` everywhere; `alldone()` also deletes temp files and runs the pan compile/replay loop | Termination must become a nonlocal return to the entry point, and the pan loop must leave the library |
| Process calls | 11 `system()`/`e_system()` sites: `cpp` preprocessing, compiling and running `pan`, `gcc-N --version` probes; `signal(SIGPIPE, alldone)` under `-X` | All of them belong to the CLI; the library takes preprocessed input and emits files |
| Output | ~2,900 lines touch `printf`/`stdout`/`stderr`; 21 files use the std streams directly | The single largest mechanical edit. See Stage 2 |
| Files written | `pan.{c,h,t,m,b,p}` and `pan.pre` in the cwd; `_spin_nvr.tmp` for inline `ltl {}` claims; `._s_p_i_n_` and `._n_i_p_s_` lexer temp files; `*.nvr` for `-f`/`-N` | Every path needs a work-directory prefix; some temp files should become memory |
| Input | Lexer reads `yyin` with `getc`/`ungetc`; the deferred-declaration pass re-reads via a temp file | A string input needs either `fmemopen`-style streams (not on Windows) or a small read abstraction in `spinlex.c` |
| Platform ifdefs | 13 `PC`/`WIN32`/`__MINGW32__` sites, including a `getline` shim | Rtools (mingw) is the Windows target because of R; CI must build there |
| Tests | None upstream; `Examples/*.pml` plus `Examples/README_tests.txt` | We write the test suite; upstream `spin` is the golden oracle |

## Scope decision (fixed here, do not relitigate without updating this file)

**In the library:**

- parse Promela and report diagnostics (`-d` symbol table dump included)
- generate the verifier source `pan.*` into a caller-chosen directory (`-a`, `-S1`/`-S2`)
- translate LTL to a never claim (`-f`, `-F`, inline `ltl {}`)
- simulate: random, guided by trail (`-t`, `-k`), bounded (`-u`); interactive only through a
  callback, never by reading `stdin`
- pretty-print / show inlined source (`-pp`, `-I`)

**In the CLI only:** option parsing, preprocessing by spawning `cpp` (the library consumes
preprocessed text), `-run`/`-search`/`-replay` and the swarm/biterate loop (compiling and
running `pan`), the xspin protocol (`-X`, `-Y`, `-Z`, `-M` msc output), `SIGPIPE` handling.

**Deliberately out:** a built-in C preprocessor, running `pan` in-process, thread safety across
instances (see Stage 3 for what *is* guaranteed).

**API shape** (names final, signatures refined in Stage 4):

```c
typedef struct spin_ctx spin_ctx;
typedef int (*spin_write_fn)(void *ud, const char *buf, size_t n);

typedef struct {
    const char   *workdir;    /* where pan.* and temp files go; NULL = cwd */
    spin_write_fn out, err;   /* diagnostics and simulation output; NULL = discard */
    void         *ud;
    unsigned      seed;
    int           verbose;    /* same bit layout as upstream's `verbose` */
} spin_options;

spin_ctx *spin_create(const spin_options *opt);
int  spin_parse(spin_ctx *, const char *path);               /* preprocessed input */
int  spin_generate(spin_ctx *, const char *path, int separate);
int  spin_ltl(spin_ctx *, const char *formula, const char *claim_name);
int  spin_simulate(spin_ctx *, const char *path, const spin_sim_options *);
const char *spin_errmsg(const spin_ctx *);                     /* last fatal message */
void spin_destroy(spin_ctx *);
```

Each `spin_*` action runs on a fresh parse. That mirrors upstream, where generation mutates
the AST (`ana_src()` dataflow and merging), so "parse once, then do several things" is not
something the code supports and the API does not pretend otherwise. Return value is 0 or a
`SPIN_E_*` code; `nr_errs` from `non_fatal()` is reported through the context.

## Stage 0 — Baseline and harness (no behaviour change) — **done**

- Make `Src/` build with `-std=c99 -Wall -Wextra` warning-free on clang and gcc; fix only what
  is needed for that. Add `-fsanitize=address,undefined` as a makefile target.
- Commit the generated parser from a pinned bison (document the version in the makefile);
  `yacc` on macOS is byacc and produces different code, so the build must not depend on which
  one happens to be installed.
- Add `tests/golden/`: for every `Examples/*.pml` (and the `LTL/` and `Exercises/` subtrees)
  record upstream's output for `spin -a`, `spin -n1 -u200` (fixed seed, bounded run), `spin -d`
  and `spin -f` on a set of formulas. A `tests/run.sh` diffs the current build against them.
  Simulation output is deterministic for a fixed seed because `Rand()` is Spin's own LCG in
  `run.c`, not `rand()`.
- GitHub Actions: ubuntu (gcc, clang), macos, windows via msys2 **mingw64** (the Rtools
  toolchain), each running the golden tests.

Exit: a green matrix that proves nothing changed, so every later stage is a diff against it.

### What Stage 0 established

172 golden cases (`tests/`), bison 3.8.2 parser committed, warning-free on gcc 13, gcc 15,
clang 17 and Apple clang, sanitizers clean on linux/clang with leak detection off, and the
golden suite passing on all four CI legs including msys2 mingw64. It took four CI rounds; the
findings that matter for later stages:

- **Compilers disagree about `-Wextra`.** gcc adds `-Wimplicit-fallthrough` (six sites) and
  gcc 15 `-Wunused-but-set-variable`; clang showed neither. "Any warning fails" only means
  something if every leg enforces it, so the matrix is not optional.
- **The preprocessor is part of spin's observable behaviour.** clang's `cpp` warns about
  nested comments in `dtp.pml`, gcc's does not, and spin passes its stderr straight through.
  The harness compares stdout only; the library in Stage 2 should never have had stderr to
  begin with. This is also an argument for the scope decision that preprocessing stays out of
  the library.
- **Windows is `-DPC`, derived from `_WIN32` now.** Without it mingw64 has no `SIGPIPE` and no
  `termios.h`. The cygwin-only gcc-4 probe inside the `PC` block is narrowed to `__CYGWIN__`.
  Everything else `PC` selects is what Windows needs, including `"wb"` for generated files.
- **`pan.h` is platform-dependent by design**, and only in one byte: `G_long` is
  `sizeof(long)` on the generating machine, 4 on mingw64. pan.c itself hashed identically on
  all legs. The harness masks that line; zuspin's tests should expect it too.
- **One real portability bug:** `isprint()` on a yacc token value in `pangen3.c`, undefined
  above 255, false on glibc/macOS, true on msvcrt. Guarded. Expect more of this class once
  the string-input path and fuzzing exist (Stage 5).
- **CI cost:** the full suite runs in ~2 minutes per leg; the msys2 leg spends most of its time
  installing. Recording goldens is maintainer-side only and must come from an unmodified
  upstream build (`tests/record.sh` says so).

## Stage 1 — Nonlocal termination and the arena

The smallest change that makes the code callable twice from one process.

- Introduce `spin_bail(int status)`: `longjmp` to a `jmp_buf` armed by the entry point. Every
  `exit()` and `alldone()` in library code becomes `spin_bail()`. `alldone()`'s side jobs are
  split: temp-file deletion into `spin_cleanup()`, the pan compile/replay loop into the CLI.
  `fatal()` keeps its message formatting but ends in `spin_bail(1)`. `tl_main.c`'s two `exit(1)`
  go the same way. `assert()` stays in Stage 1 and is reviewed in Stage 5.
- Put an arena behind `emalloc()` and `tl_emalloc()`: chunked bump allocation owned by the
  context, released in one call. `tl_mem.c`'s free lists are kept but allocate from the arena.
  Because nothing in Spin frees individually, this is sufficient for all AST, symbol table and
  generated-code buffers. `FILE *` handles are tracked by the context and closed in
  `spin_cleanup()`, which is what makes a `longjmp` from deep inside the parser safe.
- Entry point `spin_main_once(argc, argv)` wraps the old `main()` body in `setjmp`/cleanup so
  the CLI is already a library client, with a test that calls it twice.

Exit: `tests/lib/twice.c` runs two models back to back and a failing then a succeeding one,
clean under ASan and LeakSanitizer.

## Stage 2 — Output and input redirection

- `tools/redirect.sh` rewrites, mechanically and idempotently: `printf(` → `Pf(`,
  `fprintf(stdout,`/`fprintf(stderr,` → `Pf(`/`Ef(`, `fflush(stdout)` → `spin_flush()`. The
  macros expand to context-aware functions that write through `spin_options.out`/`.err`. The
  script is kept and re-run after upstream merges; the diff it produces is reviewed, never
  hand-maintained.
- `fprintf(fd_tc, …)` and the other verifier streams are left alone: they are files by design,
  opened under `workdir` (Stage 2 adds the prefix to `Cfile[].nm`, `TMP_FILE1/2`,
  `_spin_nvr.tmp`, `pan.pre`).
- Lexer input: `spinlex.c`'s `getc(yyin)`/`ungetc` go behind `spin_getc()`/`spin_ungetc()` so a
  string source can be added without `fmemopen`. The deferred-declaration temp file
  (`TMP_FILE2`) becomes a memory buffer in the context; it is the one temp file that exists only
  because the lexer wanted a second pass.
- Interactive simulation reads choices through a callback instead of `stdin`; the CLI's callback
  reads the terminal.

Exit: golden tests pass with output captured through a sink rather than `stdout`; `grep -c
'printf(' Src/*.c` outside the `Pf` macro definitions is zero; nothing in `Src/` references
`stdin`.

## Stage 3 — Globals: reset first, then instance state

Decision: do **not** hand-move 362 variables into a struct. Two steps, the second optional.

1. **Deterministic reset.** `tools/globals.sh` lists every mutable data symbol per object from
   `nm`, and the 16 function-local statics from a grep for `^\s+static`, into
   `tools/globals.txt` with its initializer. A generated `spin_reset_globals()` re-initializes
   each one (zero, or the declared initial value such as `merger = 1`). The yacc globals
   (`yychar`, `yynerrs`, `yylval`) are included. The build fails if `nm` finds a symbol the
   list does not know, so a new upstream global cannot slip in silently. Together with Stage 1
   this gives: **one instance at a time, any number of sequential calls, each starting from a
   clean state.** That is all zuspin needs, since R is single-threaded.
2. **Instance state by aliasing** (only if a second consumer needs independent instances):
   `spin_globals.h` declares `struct spin_globals` with one member per entry in
   `globals.txt` and `#define verbose (spin_g->verbose)` aliases, so upstream code is textually
   unchanged and still merges, while the state lives in the context. Shadowing conflicts
   surface as compile errors and are fixed by renaming locals. Thread safety is still not
   claimed: Spin's lexer and parser share `yylval` and friends, and a mutex around each
   `spin_*` call is the documented contract.

Exit: `tests/lib/reset.c` runs model A, then model B, then A again and gets byte-identical
output each time; the golden suite passes with every test executed in a single process.

## Stage 4 — Public API and the CLI on top of it

- `include/spin.h` with the API above, `SPIN_E_*` codes, and a `spin_version()`.
- `src/cli/main.c` is upstream's option parser plus the parts cut out in Stage 1 (preprocess via
  `cpp`, `-run`/`-replay`/swarm, xspin, msc). It links `libspin.a`. The `spin` binary must
  pass the Stage 0 golden tests unchanged.
- Build: `make lib` → `libspin.a` + header; `make spin` → the CLI; `make check`. CMake is not
  needed and R cannot use it, so keep plain make. Public symbols get a `spin_` prefix; everything
  else is hidden with `-fvisibility=hidden` where supported. Upstream names stay as they are
  inside the library so merges remain mechanical.
- Objects list for consumers: `tools/objects.sh` prints the library object list so zuspin's
  `Makevars` can be generated from it, as zusmt does for OpenSMT.

Exit: a tagged `v0.1.0` that zuspin vendors (its Stage 2).

## Stage 5 — Hardening for embedding

- `assert()` audit: those guarding argument-buffer sizes in the old `main()` move to the CLI;
  those on internal invariants become `spin_bail()` with a message. A host process must not
  abort because a Promela file was odd.
- Cancellation: `spin_options.interrupt` callback polled in the simulator loop (`sched.c`)
  and in `gensrc()`; returns through the normal bail path so cleanup runs. zuspin uses this for
  `R_CheckUserInterrupt`-style polling without a `longjmp` through Spin frames.
- Input robustness: fuzz the parser with the string input path (libFuzzer or AFL) for crashes
  that `exit()` used to hide.
- Windows/mingw: remove the `getline` shim by not using `getline`; make sure every file open
  uses `MFLAGS` and the `workdir` prefix; run the golden suite in the msys2 leg with
  `-D__USE_MINGW_ANSI_STDIO=1`, which is what R sets.

Exit: sanitizers and fuzzing clean; interrupting a long simulation leaves no temp files.

## Stage 6 — Upstream tracking

- `upstream` remote already points at nimble-code/Spin. Document the merge procedure:
  `git merge upstream/master`, re-run `tools/redirect.sh` and `tools/globals.sh`, regenerate the
  parser, run the golden suite, re-record goldens only for intentional upstream behaviour
  changes.
- Tag releases as `v<upstream>-<n>` (for example `v6.5.2-1`) so zuspin's vendor script pins a
  tag that says which Spin it carries.

## Open questions, with the current lean

- **Preprocessed input only?** Yes for the library. zuspin can run `cpp` from R with the
  compiler R itself was configured with. Promela without `#include`/`#define` parses as-is, so
  a `preprocess = FALSE` fast path costs nothing.
- **pan.* as files or memory?** Files under `workdir`. They are meant to be compiled by a C
  compiler, which wants files; a memory API would only add copying.
- **Keep `-S1`/`-S2` separate compilation?** Yes, it is a flag on the same generator, not a
  separate code path.
