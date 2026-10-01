/*
 * Several spin runs in one process. The command line is a list of spin
 * command lines separated by "--":
 *
 *     multi -- -a hello.pml -- -n1 -u50 peterson.pml -- -f "[]p"
 *
 * Each group goes through spin_main_once(); the status is printed after
 * each so the script can compare the whole output with the same runs done
 * one process each. Any difference means state leaked from one run into
 * the next, which is exactly what the generated globals reset (Stage 2)
 * is meant to make impossible.
 */
#include <stdio.h>
#include <string.h>
#include "spin_lib.h"

int
main(int argc, char *argv[])
{	int i, start = 1;

	for (i = 1; i <= argc; i++)
	{	if (i == argc || strcmp(argv[i], "--") == 0)
		{	if (i > start)
			{	/* argv[start-1] stands in for spin's argv[0] */
				int status = spin_main_once(i - start + 1, argv + start - 1);
				fflush(stdout);
				printf("spin_main_once returned %d\n", status);
			}
			start = i + 1;
	}	}
	return 0;
}
