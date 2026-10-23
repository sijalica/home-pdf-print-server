# Local test results — 21 October 2026

Command: `python -m unittest discover -s tests -v`

Result: **10 tests passed** in approximately 1.1 seconds.

Environment: Python 3.12; Flask 3.1.3; pypdf 6.10.0; temporary SQLite database. Print submission and CUPS queries simulated; PDF validation ran in a real subprocess. Expected timeout test deliberately logs an exception and still passes.

This test run did not access the Toshiba, printer, systemd, firewall or production history. It establishes the listed application behaviors only. Gunicorn startup, real CUPS integration, reboot behavior, timer operation and spool-file retention of the revised release require the Toshiba acceptance checklist.
## Toshiba verification — 23 October 2026

All 11 automated tests passed.

A real PDF printed successfully. Cleanup removed the uploaded copy,
and its SQLite history remained marked completed.

CUPS omitted job-name, including in administrator queries.
For recorded CUPS IDs, cleanup now verifies the ID and printer queue,
and checks the title when available. Missing titles no longer cause
a false mismatch. A regression test confirms that a different printer
still prevents deletion.

Limitation: this assumes CUPS has not reset its job database and reused
job IDs. Jobs without a recorded CUPS ID still require reconciliation.

Reboot recovery remains to be verified.
