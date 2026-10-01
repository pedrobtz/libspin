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

## Stage 1 — Nonlocal termination and the arena — **done**

The smallest change that removes process termination and process-lifetime memory from the
library. Calling it twice in one process is Stage 2 (globals), which this stage makes possible.

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
  the CLI is already a library client.

Exit: `tests/lib/once.c` gets control back, with the right status, on every termination path
(normal, `fatal()` in the parser, `fatal()` after parsing, usage, LTL `Fatal()`, missing files);
the golden suite is unchanged; the Linux sanitizer leg runs with LeakSanitizer on and reports
nothing.

### What Stage 1 established

- `Src/spin_lib.{c,h}`: `spin_bail()`, the arena, the file registry, `spin_cleanup()`,
  `spin_main_once()`. `Src/spin_cli.c` is the only `main()`. `Src/libspin.a` is everything else.
- Every `exit()` is gone from library code; `alldone()` and both `fatal()`s end in `spin_bail()`.
  `pangen5.c` and `msc_tcl.c` carried their own `extern void exit(int)` declarations, removed.
- `emalloc()` is the arena; `tl_emalloc()` already sat on top of it. The one `getline()` buffer
  that outlived the call (`-F` formula file) is copied into the arena. The `-f`/inline `ltl`
  `getline()` buffer was already freed by upstream.
- `fopen`/`fclose` → `spin_fopen`/`spin_fclose` everywhere (a `perl -pi` one-liner; see the
  commit), so a bail from inside the parser closes `pan.*` and the never-claim temp file.
- What still relies on the process: `signal(SIGPIPE, alldone)` under `-X`, the `system()`
  calls, and bison's parser stack if a bail happens after it grew past 200 entries (bison
  mallocs then; `yyparse` would have freed it). All three are CLI or Stage 4/5 matters.
- macOS has no LeakSanitizer; `leaks --atExit` confirmed zero leaks on the five paths above,
  and the `sanitize` target sets `detect_leaks` from `uname`.

## Stage 2 — Globals: reset first, then instance state — **step 1 done**

(Swapped with output redirection after Stage 1: the "callable twice" test needs a reset, not
redirected output, and a stale symbol table pointing into a released arena is a use-after-free
waiting to happen, so this comes first.)

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

Exit: `tests/lib/multi.c` runs model A, then model B, then A again and gets byte-identical
output each time, including a fatal parse error between two good runs, and `pan.c` from a
second generation in one process hashes like a fresh one.

### What step 1 established

- **The list is the compiler's, not ours.** `tools/globals.py` builds every TU at `-O0` in a
  scratch copy, asks `nm` for writable symbols (432 across 29 TUs), and refuses to proceed if
  any is a function-local static (dotted name). `-O0` matters: clang at `-O2` splits
  `static int EPT[2]` into `EPT.0`/`EPT.1`, which looks exactly like a function-local static.
- **26 function-local statics were hoisted by hand** to file scope, same name, same
  initialiser, just before their function. That is the only hand edit the reset needs, and it
  is what makes a reset possible at all.
- **No type parsing.** A zero-initialised symbol is `memset`; an initialised one gets a copy
  of `static const __typeof__(x) spin_init_x = <initialiser text verbatim>`. The initialiser
  text comes from a small statement scanner over the TU and its quoted includes (the
  `pangen*.h` code tables are definitions in headers). The scanner had to learn Spin's habits:
  multi-line `#define`s, prose inside `#if 0`, the `#else` of `#if 1`, conditionals *inside*
  table initialisers (kept verbatim so both copies compile the same elements), and the
  upstream `"" "void"` adjacency that only exists in dead code.
- **The multi-run test earned its keep on day one.** The first generation missed every
  uninitialised external (`Fname`, `verbose`, `fsm_tbl`, 97 symbols): Mach-O reports those as
  `(common)` with a different `nm -m` line format. Single runs and the whole golden suite
  passed anyway; the second run in one process was a use-after-free into the released arena.
- **Guards travel with the symbol.** A declaration under `#ifndef PC` resets under
  `#ifndef PC`, so the mingw64 build, where the symbol does not exist, compiles.
- **One include line per TU**, at the end of the file (and of `spin.y`'s epilogue), is the
  whole footprint in upstream code. `make globals-check` in CI fails when a new upstream
  global appears without regenerating.
- `spin_main_once()` resets before every run, so the first run is also a reset run and the
  golden suite exercises the reset code on every case.

Step 2 (instance state via `struct spin_globals` and macro aliases) remains deferred until a
consumer needs independent instances.

## Stage 3 — Output and input redirection — **done**

Decided differently from the first plan, after the survey: besides ~2,900 `printf` calls,
many helpers take a `FILE *` that callers pass `stdout` into (`comment(stdout, …)`,
`sr_mesg(stdout, …)`, `yyin = stdin`, `tl_out = stdout`), so rewriting calls would have missed
them. The rewrite is of the **stream names**:

| upstream | library |
| --- | --- |
| `stdout`, `stderr`, `stdin` | `spin_out`, `spin_err`, `spin_in` (`FILE *` owned by `spin_lib.c`) |
| `printf(` | `spin_printf(` (vfprintf to `spin_out`) |
| `getchar()` | `getc(spin_in)` |

`tools/redirect.py` does it token-aware (nothing inside string or character literals or
comments is touched; `pangen*.c` emit C source containing these words as text), is idempotent,
and has a `--check` mode that CI runs. `spin_main_once()` points any stream still `NULL` at
the real one, so the CLI needs no setup; an embedder calls `spin_set_streams()`. The streams
live in `spin_lib.c`, which the globals reset excludes, so they persist across runs.

What this does **not** cover, on purpose: the verifier streams (`fd_tc`, `fd_th`, …) are files
under the work directory and stay `fprintf`; the work-directory prefix for them is Stage 4's
API work, where `spin_fopen()` is the one place to add it.

- `tests/lib/capture.c` runs with `spin_out`/`spin_err` on temporary files and compares with
  console output on eleven command lines; captured stderr must be empty, confirming Spin's
  diagnostics all go to stdout.
- Interactive simulation (`-i`) now reads from `spin_in`; a callback-based variant is left for
  the API stage if zuspin wants it.

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
