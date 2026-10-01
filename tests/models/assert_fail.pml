/* A simulation that trips an assertion: the error reporting path, not a parse error. */
byte n = 0;
active [2] proctype inc()
{
	byte t;
	t = n; n = t + 1;
	assert(n <= 1)
}
