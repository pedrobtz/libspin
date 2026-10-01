# libspin top-level make. Upstream's version of this file only forwarded
# all/install/clean to Src/makefile; those targets are kept as they were
# and the libspin ones are added below. Src/makefile builds the spin
# binary and is upstream's.
#
#   make            build Src/spin
#   make check      build, then run the golden suite and the library tests
#   make sanitize   rebuild with ASan+UBSan and run both under them
#   make parser     regenerate Src/y.tab.[ch] with bison 3.8 (see Src/makefile)
#   make install    install spin and its man page (upstream target)
#   make clean

CC ?= cc
CFLAGS ?= -std=gnu99 -O2 -DNXT -Wall -Wextra -pedantic
SAN_CFLAGS = -std=gnu99 -O1 -g -DNXT -Wall -Wextra -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer
SAN_LDFLAGS = -fsanitize=address,undefined

# LeakSanitizer is not available on macOS; everywhere else the arena behind
# emalloc() and the file registry (Src/spin_lib.c) mean a run should leak
# nothing, so the golden suite doubles as the leak test.
LEAKS ?= $(shell [ "$$(uname -s)" = Darwin ] && echo 0 || echo 1)
SAN_ENV = ASAN_OPTIONS=detect_leaks=$(LEAKS) UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1

all:
	$(MAKE) -C Src CC="$(CC)"

install:
	$(MAKE) -C Src install

tests/lib/once: tests/lib/once.c Src/libspin.a Src/spin_lib.h
	$(CC) $(CFLAGS) -ISrc -o $@ tests/lib/once.c Src/libspin.a $(LDFLAGS)

check: all tests/lib/once
	sh tests/run.sh Src/spin
	sh tests/lib/run.sh tests/lib/once

sanitize:
	$(MAKE) -C Src clean
	rm -f tests/lib/once
	$(MAKE) -C Src CC="$(CC)" CFLAGS="$(SAN_CFLAGS)" LDFLAGS="$(SAN_LDFLAGS)"
	$(MAKE) tests/lib/once CC="$(CC)" CFLAGS="$(SAN_CFLAGS)" LDFLAGS="$(SAN_LDFLAGS)"
	$(SAN_ENV) sh tests/run.sh Src/spin
	$(SAN_ENV) sh tests/lib/run.sh tests/lib/once
	$(MAKE) -C Src clean
	rm -f tests/lib/once

parser:
	$(MAKE) -C Src parser

clean:
	$(MAKE) -C Src clean
	rm -f tests/lib/once

.PHONY: all install check sanitize parser clean
