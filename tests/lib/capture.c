/*
 * Output capture: run one spin command line with spin_out and spin_err
 * pointed at temporary files instead of the console, then print what was
 * captured, each stream under a marker. The script compares the stdout
 * part with the same run through tests/lib/once (real stdout), and the
 * stderr part must be empty: Spin writes its diagnostics to stdout.
 *
 * This is the whole point of Stage 3: an embedder decides where output
 * goes, and nothing in the library can reach the console behind its back.
 */
#include <stdio.h>
#include "spin_lib.h"

static void
dump(FILE *fp, const char *marker)
{	int c;

	printf("%s\n", marker);
	rewind(fp);
	while ((c = getc(fp)) != EOF)
	{	putchar(c);
	}
}

int
main(int argc, char *argv[])
{	FILE *out = tmpfile(), *err = tmpfile();
	int status;

	if (!out || !err)
	{	fprintf(stderr, "capture: tmpfile failed\n");
		return 2;
	}
	spin_set_streams(NULL, out, err);
	status = spin_main_once(argc, argv);
	fflush(out); fflush(err);
	dump(out, "--- captured stdout ---");
	printf("spin_main_once returned %d\n", status);
	dump(err, "--- captured stderr ---");
	return 0;
}
