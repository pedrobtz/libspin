/*
 * Library smoke test: spin_main_once() must *return* the status that
 * upstream spin would have exited with, on the success path and on every
 * failure path, with the process still alive afterwards. Called with a
 * spin command line; prints the status on a line of its own so the
 * script can check it, and exits 0 only if control came back here.
 *
 * Deliberately one call per process: the globals are not reset yet
 * (roadmap Stage 2), so a second call would run on stale state.
 */
#include <stdio.h>
#include "spin_lib.h"

int
main(int argc, char *argv[])
{	int status = spin_main_once(argc, argv);

	fflush(stdout);
	printf("spin_main_once returned %d\n", status);
	return 0;
}
