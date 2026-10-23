# Operations

Run from the Toshiba under the project owner. The web service uses a virtual-environment executable explicitly; systemd does not need `source activate`.

| Task | Command |
|---|---|
| Web status | `systemctl --user status print-server.service --no-pager` |
| Reload edited code | `systemctl --user restart print-server.service` |
| Web logs | `journalctl --user -u print-server.service -n 50 --no-pager` |
| Cleanup logs | `journalctl --user -u print-cleanup.service -n 50 --no-pager` |
| Timer schedule | `systemctl --user list-timers print-cleanup.timer` |
| Run maintenance now | `systemctl --user start print-cleanup.service` |
| Printer state | `lpstat -p -d` |
| Outstanding jobs | `lpstat -o` |
| Local listeners | `ss -ltn` |

An inactive oneshot cleanup service between successful runs is normal; inspect exit status and timer. Linger keeps user services available without an interactive login, but does not stop laptop sleep. Reboot/sleep tests are required separately.

## Needs-review jobs

Never press Upload again to recover an uncertain job. Inspect CUPS job attributes and compare the UUID title, queue, time and owner. Maintenance attempts title matching automatically for new jobs. If a unique job is found it records the ID; if missing/ambiguous it retains the file. Do not assume a missing CUPS record means it never printed. Resolve manually and document your evidence before deciding to create a new print request.

Legacy saved rows lack the new title/token information. Inspect them individually and explicitly cancel/reconcile or remove their files after checking the original job. No migration or cleanup guesses that an old saved row is safe to print.

## Disk and logs

Check `df -h` and `du -sh instance/uploads` periodically. History contains original filenames and self-reported names: protect SQLite and journal access. Do not publish terminal dumps containing personal documents. Keep journal rotation enabled; review host snapshots for retained uploads. No report program was added because reporting is deferred by request.

## Backups

Use SQLite's backup API for a consistent metadata backup; keep it private. Exclude documents, CUPS spool, .venv and secret.key from Git. Back up the secret separately only if session continuity is important; changing it expires all browser sessions and result access. Backups of metadata also retain filenames. Never restore old state and automatically resubmit jobs.

## Learning map

Python `with database()` corresponds to transaction and resource scope. `subprocess.run([...])` resembles Java ProcessBuilder. `?` SQL placeholders resemble PreparedStatement. systemd manages process lifecycle; CUPS manages printing. A browser session identifies a client session, not a verified person. A timer is scheduling, not proof that its last execution succeeded.
