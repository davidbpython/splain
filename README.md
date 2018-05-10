# splain
## explain exceptions and offer debugging advice 

Usage:
```
import splain
```

`splain` attempts to explain any exceptions that result in program termination.  

When `splain` is imported, it redirects and buffers STDERR until program termination.  At program termination, `splain` reads any text written to STDERR and uses pattern matching to determine whether an exception occurred.

If it appears that an exception occurred, `splain` attempts to identify the error type and other elements of the exception message (error line, line number, etc.).  It displays these elements in a clearer form and provides a full explanation of the error type and its meaning, and offers debugging advice.  

Note:  `splain` bufffers STDERR and does not display error messages until program termination (including non-exception errors written to STDERR).  

Any text written to STDERR will be displayed only upon program termination.  


