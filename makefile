# libspin top-level make. Upstream's version of this file only forwarded
# all/install/clean to Src/makefile; those targets are kept as they were
# and the libspin ones are added below. Src/makefile builds the spin
# binary and is upstream's.
#
#   make            build Src/spin
#   make check      build, then run the golden suite (tests/run.sh)
#   make sanitize   rebuild with ASan+UBSan and run the suite under them
#   make parser     regenerate Src/y.tab.[ch] with bison 3.8 (see Src/makefile)
#   make install    install spin and its man page (upstream target)
#   make clean

CC ?= cc

all:
	$(MAKE) -C Src CC="$(CC)"

install:
	$(MAKE) -C Src install

check: all
	sh tests/run.sh Src/spin

# Leak detection is off on purpose for now: upstream spin frees nothing and
# relies on process exit, so every run would report leaks. Stage 1 of
# roadmap.md puts an arena behind emalloc(); when that lands this becomes
# detect_leaks=1 and the suite doubles as the leak test.
sanitize:
	$(MAKE) -C Src clean
	$(MAKE) -C Src CC="$(CC)" \
	  CFLAGS="-std=gnu99 -O1 -g -DNXT -Wall -Wextra -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer" \
	  LDFLAGS="-fsanitize=address,undefined"
	ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 sh tests/run.sh Src/spin
	$(MAKE) -C Src clean

parser:
	$(MAKE) -C Src parser

clean:
	$(MAKE) -C Src clean

.PHONY: all install check sanitize parser clean
