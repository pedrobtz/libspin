#!/bin/sh
# Runs sequences of spin invocations in one process (tests/lib/multi) and
# compares the combined output with the same invocations run one process
# each (tests/lib/once). Arguments: path to multi, path to once.
set -u
multi=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
once=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
here=$(cd "$(dirname "$0")" && pwd)
examples=$here/../../Examples
models=$here/../models
fail=0

scratch=$(mktemp -d "${TMPDIR:-/tmp}/libspin-multi.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
cp "$examples/hello.pml" "$examples/peterson.pml" "$examples/leader0.pml" "$examples/LTL/train.pml" "$models"/*.pml "$scratch"
cd "$scratch" || exit 2

# sequence NAME group -- group -- group ...
sequence() {
  name=$1; shift
  "$multi" -- "$@" </dev/null >multi.out 2>/dev/null
  rm -f pan.* ; : > once.out
  group=""
  for a in "$@" --; do
    if [ "$a" = "--" ]; then
      if [ -n "$group" ]; then
        # shellcheck disable=SC2086
        eval "\"\$once\" $group" </dev/null >>once.out 2>/dev/null
        group=""
      fi
    else
      group="$group '$(printf '%s' "$a" | sed "s/'/'\\\\''/g")'"
    fi
  done
  if cmp -s multi.out once.out; then
    echo "ok   $name"
  else
    echo "FAIL $name"; diff -u once.out multi.out | head -40 | sed 's/^/     /'; fail=$((fail + 1))
  fi
}

# A, B, A: the third run must equal the first byte for byte
sequence "sim A B A"        hello.pml -- -n1 -u100 -p peterson.pml -- hello.pml   # peterson never ends unbounded
# failure then success: a fatal() mid-parse must not poison the next parse
sequence "fail then ok"     -a bad_syntax.pml -- -a hello.pml -- -a bad_undeclared.pml -- hello.pml
# generation twice: the second pan.c must hash like a fresh one (compared via stdout+status here,
# and by the golden suite's hashes when run in one process below)
sequence "gen gen"          -a leader0.pml -- -a peterson.pml -- -a leader0.pml
# LTL translator state (tl_*: its own allocator, caches, state counters)
sequence "ltl ltl"          -f "[](p U q)" -- -f "<>p" -- -f "[](p U q)"
# inline ltl claims and a symbol table dump between simulations
sequence "mixed"            -n1 -u50 -p train.pml -- -d hello.pml -- -f "[]p" -- -n1 -u50 -p train.pml -- -a bad_never_io.pml -- -d hello.pml

# pan.c from a second generation in the same process must equal a fresh one
"$once" -a leader0.pml </dev/null >/dev/null 2>&1; fresh=$(cksum < pan.c)
"$multi" -- -a peterson.pml -- -a leader0.pml </dev/null >/dev/null 2>&1; again=$(cksum < pan.c)
if [ "$fresh" = "$again" ]; then echo "ok   pan.c after a prior generation"; else echo "FAIL pan.c differs after a prior generation"; fail=$((fail + 1)); fi

echo "$((6 - fail)) passed, $fail failed"
exit $fail
