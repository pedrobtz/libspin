/***** libspin: spin_lib.h *****/

/*
 * Process-lifetime services that upstream Spin got from being a program:
 * termination, memory that is reclaimed at exit, and files that are closed
 * at exit. Included from spin.h and tl.h so every translation unit sees
 * the same declarations. See roadmap.md, Stage 1.
 */

#ifndef SPIN_LIB_H
#define SPIN_LIB_H

#include <stddef.h>
#include <stdio.h>

/* Ends the current spin_main_once() with this status. Never returns.
 * Replaces exit() throughout the library; alldone() and fatal() end here. */
void	spin_bail(int status);

/* Arena behind emalloc(): bump allocation, released as a whole by
 * spin_cleanup(). Returns NULL only when malloc fails. Not zeroed. */
void	*spin_arena_alloc(size_t n);

/* fopen/fclose that register the handle, so that a bail from deep inside
 * the parser or the generator still closes every file in spin_cleanup(). */
FILE	*spin_fopen(const char *path, const char *mode);
int	spin_fclose(FILE *fp);

/* The console, as far as the library is concerned. tools/redirect.py has
 * rewritten every stdout/stderr/stdin and printf in library code to these;
 * spin_main_once() points any that are still NULL at the real streams, so
 * the CLI needs no setup and an embedder sets them before calling. */
extern FILE	*spin_out, *spin_err, *spin_in;
int	spin_printf(const char *fmt, ...);
void	spin_set_streams(FILE *in, FILE *out, FILE *err);	/* NULL keeps the current one */

/* Closes registered files and releases the arena. Called by
 * spin_main_once(); safe to call when nothing is open or allocated. */
void	spin_cleanup(void);

/* Upstream's main(), renamed. Returns a status or ends via spin_bail(). */
int	spin_main_body(int argc, char *argv[]);

/* Runs spin_main_body() with a bail target armed, then spin_cleanup().
 * Always returns: the status spin would have exited with. */
int	spin_main_once(int argc, char *argv[]);

#endif
