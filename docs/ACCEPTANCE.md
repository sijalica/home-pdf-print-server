# Acceptance and evidence

## Already observed on the original Toshiba version

- USB printer detected; HP plugin installed; test page physically printed.
- Plain-text and PDF jobs physically printed.
- SQLite submission name and CUPS ID matched the browser response.
- CUPS state 9 observed; cleanup removed uploaded copies for jobs 6 and 8.
- CUPS retention configuration validated and service restarted.
- User timer, linger and Gunicorn service were active.
- Web page loaded through SSH tunnel.

These are user-reported results from the guided build, not proof that this replacement release has been deployed.

## Replacement-release automated tests

Run `python -m unittest discover -s tests -v`. Tests create a temporary database and PDFs and simulate lp/CUPS; they never print or connect to the printer. Covered behaviors: valid upload; GET refresh; duplicate token; malformed PDF; missing token; other-session result denial; filename handling; ambiguous submission timeout; completed-file cleanup with retained history; CUPS lookup failure retention; repeat migration preserving data. See tests/test_app.py for exact assertions.

## Toshiba release acceptance (pending)

- [ ] Back up source/config/history, install package, migrate successfully.
- [ ] Run automated tests on Toshiba and record output and package versions.
- [ ] Open a fresh form through SSH; upload a single one-page non-sensitive PDF.
- [ ] Verify one physical page, numeric CUPS ID and matching SQLite record.
- [ ] Refresh result page twice; verify no extra print.
- [ ] Within a normal maintenance interval, refresh result and verify completed/deleted; confirm source file absent and metadata retained.
- [ ] Confirm CUPS does not retain the completed document; inspect as administrator without modifying spool files. Keep metadata needed for reconciliation.
- [ ] Use a fake .pdf text file: rejected, no print, no retained source file.
- [ ] Disconnect SSH and confirm services continue from a new session.
- [ ] Reboot with no active jobs; reconnect, verify services/timer and unchanged printer queue. Browser form and status must work.
- [ ] Check listeners: app should remain 127.0.0.1:5000. No direct LAN claim.
- [ ] Review legacy saved/uncertain files manually and remove only after reconciliation.

Do not intentionally fill the real disk or repeatedly print for testing. Use mocks for resource failures and duplicates. A deliberate printer-off test should use one dummy job, with a clear cancellation/recovery plan to avoid printing it unexpectedly later.

## Evidence template

Date / environment / revision / action / expected result / actual result / sanitized screenshot or output / limitation / restoration step.

Use generic filenames such as sample.pdf and Test user in portfolio evidence. Never include real identity documents, credentials, secret.key, the live SQLite database or upload files.
