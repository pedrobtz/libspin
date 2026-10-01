#!/bin/sh
# Library-level tests. Argument: path to the built tests/lib/once program.
# Each case runs once and expects control to return with a given status.
set -u
once=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
here=$(cd "$(dirname "$0")" && pwd)
models=$here/../models
examples=$here/../../Examples
fail=0

expect() {  # expect STATUS args...
  want=$1; shift
  got=$("$once" "$@" </dev/null 2>/dev/null | sed -n 's/^spin_main_once returned //p')
  if [ "$got" = "$want" ]; then
    echo "ok   returned $want: spin $*"
  else
    echo "FAIL expected $want, got '${got:-no return}': spin $*"; fail=$((fail + 1))
  fi
}

scratch=$(mktemp -d "${TMPDIR:-/tmp}/libspin-lib.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
cp "$examples/hello.pml" "$models"/*.pml "$scratch"
cd "$scratch" || exit 2

expect 0 -V                                   # alldone(0) from option parsing
expect 0 hello.pml                            # normal simulation, alldone(nr_errs)
expect 0 -a hello.pml                         # verifier generation
expect 1 -a bad_syntax.pml                    # fatal() during parsing
expect 1 -a bad_undeclared.pml                # fatal() after parsing
expect 1 nosuchfile.pml                       # preprocessing failure
expect 1 -F nosuchfile.ltl hello.pml          # cannot open formula file
expect 0 -f "[](p U q)"                       # tl_main() path, no model
expect 1 -f "[](p U"                          # LTL syntax error: Fatal() in tl_*
expect 1 -o9 hello.pml                        # usage() -> alldone(1)
expect 1 -f                                   # missing -f argument

echo "$((11 - fail)) passed, $fail failed"
exit $fail
