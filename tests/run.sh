#!/bin/sh
# Compare a spin binary against tests/golden/.
#
#   tests/run.sh [path/to/spin]      default: Src/spin
#
# Exit status is the number of failing cases (capped at 125). Each failure
# prints a unified diff; set VERBOSE=1 to also list passing cases.
. "$(dirname "$0")/lib.sh"

spin=$(cd "$(dirname "${1:-$root/Src/spin}")" && pwd)/$(basename "${1:-$root/Src/spin}")
[ -x "$spin" ] || { echo "run.sh: $spin is not executable" >&2; exit 2; }
[ -d "$golden" ] || { echo "run.sh: no $golden; run tests/record.sh first" >&2; exit 2; }

make_scratch
trap 'rm -rf "$scratch"' EXIT
pass=0 fail=0

check() {
  name=$1 kind=$2 arg=$3
  want=$golden/$kind/$name.out
  got=$scratch/$kind-$name.got
  if [ "$kind" = ltl ]; then run_ltl "$spin" "$arg" > "$got"
  else run_case "$spin" "$kind" "$arg" > "$got"; fi
  if [ ! -f "$want" ]; then
    echo "NEW  $kind/$name (no golden file)"; fail=$((fail + 1))
  elif cmp -s "$want" "$got"; then
    [ "${VERBOSE:-0}" = 1 ] && echo "ok   $kind/$name"; pass=$((pass + 1))
  else
    echo "FAIL $kind/$name"; diff -u "$want" "$got" | sed 's/^/     /'; fail=$((fail + 1))
  fi
}
for_each_case check
echo "$pass passed, $fail failed ($spin)"
[ "$fail" -gt 125 ] && exit 125
exit "$fail"
