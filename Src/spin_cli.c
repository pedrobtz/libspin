/***** libspin: spin_cli.c *****/

/*
 * The spin executable. Everything else is the library; this is the only
 * translation unit with a main(). Stage 4 of roadmap.md moves option
 * parsing and the pan compile/run loop here as well.
 */

#include "spin_lib.h"

int
main(int argc, char *argv[])
{
	return spin_main_once(argc, argv);
}
