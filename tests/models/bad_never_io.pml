/* non_fatal() on a never claim with i/o, then normal completion with errors counted. */
chan c = [1] of { byte };
active proctype p() { c!1; c?_ }
never { do :: c?1 od }
