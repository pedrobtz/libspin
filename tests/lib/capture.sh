#!/bin/sh
# Compare captured output (tests/lib/capture, streams redirected to files)
# with console output (tests/lib/once) for the same spin command lines.
# Arguments: path to capture, path to once.
set -u
capture=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
once=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
here=$(cd "$(dirname "$0")" && pwd)
examples=$here/../../Examples
models=$here/../models
fail=0 n=0

scratch=$(mktemp -d "${TMPDIR:-/tmp}/libspin-capture.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
cp "$examples/hello.pml" "$examples/peterson.pml" "$examples/LTL/train.pml" "$models"/*.pml "$scratch"
cd "$scratch" || exit 2

case_() {
  n=$((n + 1))
  "$capture" "$@" </dev/null >cap.out 2>cap.console
  "$once" "$@" </dev/null >once.out 2>/dev/null
  # expected: marker, once's stdout verbatim (which ends with the status line), marker, nothing
  { echo "--- captured stdout ---"; cat once.out; echo "--- captured stderr ---"; } >want.out
  if cmp -s want.out cap.out && [ ! -s cap.console ]; then
    echo "ok   captured: spin $*"
  else
    echo "FAIL captured: spin $*"; diff -u want.out cap.out | head -20 | sed 's/^/     /'
    [ -s cap.console ] && { echo "     leaked to the console:"; head -5 cap.console | sed 's/^/     /'; }
    fail=$((fail + 1))
  fi
}

case_ hello.pml
case_ -n1 -u100 -p -g -l -r -s peterson.pml
case_ -d hello.pml
case_ -a hello.pml
case_ -a bad_syntax.pml
case_ -a bad_undeclared.pml
case_ -n1 -u50 -p train.pml
case_ -f "[](p U q)"
case_ -f "[](p U"
case_ -V
case_ -o9 hello.pml

echo "$((n - fail)) passed, $fail failed"
exit $fail
