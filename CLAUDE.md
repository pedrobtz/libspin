# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`libspin` turns Spin, the Promela model checker from nimble-code/Spin, into an embeddable C
library and rebuilds the `spin` command-line tool as a thin wrapper over it. Its first consumer
is the R package [zuspin](https://github.com/pedrobtz/zuspin), checked out at `../zuspin`, which
vendors a pinned tag of this repository. Work here is paced by [roadmap.md](roadmap.md); read
the "What we are starting from" table there before touching `Src/`.

## Upstream relationship

`main` was seeded from upstream `master` (Spin 6.5.2) and the `upstream` remote points at
nimble-code/Spin. Every change is judged by whether `git merge upstream/master` will still be
mechanical afterwards:

- Upstream identifiers, file names and formatting stay as they are inside `Src/`. New code is
  added beside them, prefixed `spin_`.
- Sweeping edits (output redirection, globals reset) are produced by scripts under `tools/`
  that are idempotent and re-run after a merge, never maintained by hand.
- `Src/LICENSE` is upstream's BSD 3-Clause text and stays verbatim.

## Building and testing

```sh
make -C Src                 # upstream build, still the reference until Stage 4
make -C Src CC=clang CFLAGS="-fsanitize=address,undefined -g -DNXT"
```

The generated parser is produced with bison, not the system `yacc` (byacc on macOS), and is
committed so consumers never run a parser generator. `tests/run.sh` diffs the current build
against `tests/golden/`, which was recorded from upstream `spin`; re-record a golden file only
for an intentional behaviour change and say why in the commit.

## Rules that fall out of the design

- No `exit()`, `abort()` or bare `assert()` in library code: termination is `spin_bail()`, which
  longjmps to the entry point after which `spin_cleanup()` releases the arena and closes files.
- No `printf`/`stdout`/`stderr`/`stdin` in library code: output goes through `Pf()`/`Ef()` to
  the context's sinks, input through `spin_getc()`.
- No `system()`, `signal()`, `chdir()` or `getenv()` in library code. Preprocessing and running
  `pan` are the CLI's job.
- Every file the library creates is opened under the context's `workdir`.
- The library guarantees sequential re-use from one thread, not concurrent instances. Say so in
  any API documentation rather than implying more.
