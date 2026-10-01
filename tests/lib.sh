# Shared by tests/run.sh and tests/record.sh. POSIX sh.
#
# A "case" is one spin invocation on one input; its result is a text file:
# stdout and stderr merged, then the exit status, then for the generator case
# a checksum per pan.* file. pan.c alone is ~330 KB per model, so the generated
# sources are compared by checksum rather than stored; a mismatch names the
# file, and the reference binary (upstream `spin` built from the `upstream`
# remote) regenerates it for a real diff.
#
# Every case runs in a scratch copy of Examples/ and tests/models/, inside the
# model's own directory, with the model named by its basename. That keeps
# paths out of the recorded output and keeps spin's work files (pan.*,
# _spin_nvr.tmp, *.trail) out of the tree.
#
# stdin is always tests/stdin.txt: Promela has a predefined STDIN channel
# (Examples/wordcount.pml uses it) and a simulation that reads it would
# otherwise block on the terminal.

set -u

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)
golden="$here/golden"

if command -v sha256sum >/dev/null 2>&1; then
  sha256() { sha256sum "$1" | cut -c1-64; }
else
  sha256() { shasum -a 256 "$1" | cut -c1-64; }
fi

# Models under test, as paths relative to the scratch root. Book_1991 is left
# out: it is pre-6.x Promela with its own header layout and several of its
# models do not parse with current spin.
list_models() {
  (cd "$root/Examples" && ls *.pml LTL/*.pml Exercises/*.pml) | sed 's#^#Examples/#'
  (cd "$here/models" && ls *.pml) | sed 's#^#models/#'
}

# Case name from a model path: Examples/LTL/train.pml -> Examples_LTL_train
case_name() { printf '%s' "$1" | sed 's#\.pml$##; s#/#_#g'; }

make_scratch() {
  scratch=$(mktemp -d "${TMPDIR:-/tmp}/libspin-tests.XXXXXX")
  cp -R "$root/Examples" "$scratch/Examples"
  cp -R "$here/models" "$scratch/models"
}

# run_case SPIN KIND MODEL -> result on stdout
#   sim  bounded random simulation with a fixed seed and every trace flag
#   gen  verifier generation
#   sym  symbol table dump
run_case() {
  spin=$1 kind=$2 model=$3
  dir=$scratch/$(dirname "$model")
  base=$(basename "$model")
  (
    cd "$dir" || exit 97
    rm -f pan.* _spin_nvr.tmp ./*.trail
    case $kind in
      sim) "$spin" -n1 -u200 -p -g -l -r -s "$base" < "$here/stdin.txt" 2>&1; echo "exit: $?" ;;
      gen) "$spin" -a "$base" < "$here/stdin.txt" 2>&1; echo "exit: $?"
           for f in pan.b pan.c pan.h pan.m pan.p pan.t; do
             [ -f "$f" ] && echo "sha256 $f $(sha256 "$f")"
           done ;;
      sym) "$spin" -d "$base" < "$here/stdin.txt" 2>&1; echo "exit: $?" ;;
    esac
    rm -f pan.* _spin_nvr.tmp ./*.trail
    exit 0
  )
}

# run_ltl SPIN FORMULA -> result on stdout
run_ltl() {
  ( cd "$scratch" && "$1" -f "$2" < "$here/stdin.txt" 2>&1; echo "exit: $?" )
}

# for_each_case CALLBACK: CALLBACK NAME KIND ARG, for every case
for_each_case() {
  cb=$1
  for m in $(list_models); do
    n=$(case_name "$m")
    for k in sim gen sym; do "$cb" "$n" "$k" "$m"; done
  done
  i=0
  while IFS= read -r f; do
    case $f in ''|'#'*) continue ;; esac
    i=$((i + 1))
    "$cb" "$(printf 'ltl_%02d' "$i")" ltl "$f"
  done < "$here/ltl-formulas.txt"
}
