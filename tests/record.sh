#!/bin/sh
# Re-record tests/golden/ from a reference spin binary.
#
#   tests/record.sh [path/to/spin]
#
# The reference is upstream spin, built unmodified from the `upstream` remote;
# default is Src/spin, which is only right before libspin changes behaviour.
# Re-recording after an intentional change is fine, but say which cases and
# why in the commit message, because the diff of tests/golden/ *is* the
# behaviour change.
. "$(dirname "$0")/lib.sh"

spin=$(cd "$(dirname "${1:-$root/Src/spin}")" && pwd)/$(basename "${1:-$root/Src/spin}")
[ -x "$spin" ] || { echo "record.sh: $spin is not executable" >&2; exit 2; }

make_scratch
trap 'rm -rf "$scratch"' EXIT
rm -rf "$golden"
mkdir -p "$golden"

record() {
  name=$1 kind=$2 arg=$3
  out=$golden/$kind/$name.out
  mkdir -p "$golden/$kind"
  if [ "$kind" = ltl ]; then run_ltl "$spin" "$arg" > "$out"
  else run_case "$spin" "$kind" "$arg" > "$out"; fi
}
for_each_case record
echo "recorded $(find "$golden" -name '*.out' | wc -l | tr -d ' ') cases from $spin"
