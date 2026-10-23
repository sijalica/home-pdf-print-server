# Upgrade the existing Toshiba project

This procedure keeps `instance/`, your existing database, upload files, `.venv`, Git repository and old migration scripts. It does not alter UFW, SSH, CUPS or router settings. Do not unzip directly over the running project.

## 1. Transfer and stage

Download the supplied ZIP on Windows, then copy it using a new local PowerShell tab. Replace the source path with its actual location:

```powershell
scp "C:\Users\YourName\Downloads\Home_Print_Server_Portfolio.zip" pritilend@192.168.0.21:~/
```

In Toshiba SSH, extract to a new staging directory using Python (no unzip package needed):

```bash
mkdir -p ~/print-server-staging
python3 -m zipfile -e ~/Home_Print_Server_Portfolio.zip ~/print-server-staging
```

The ZIP contains `print-server-release/`. Inspect its README and these instructions in Vim before proceeding.

## 2. Stop services and back up the current working state

Do this with no active uploads. Stopping the web service does not cancel jobs already in CUPS.

```bash
systemctl --user stop print-server.service print-cleanup.timer print-cleanup.service
cd ~/projects/print-server
```

Save your current source changes to Git after reviewing them; do not commit PDFs or databases. Then create a private backup folder:

```bash
mkdir -m 700 ~/print-server-backup-before-release
```

If that directory already exists, use a new name consistently below; do not overwrite an older backup. Back up source and service configuration without uploads:

```bash
tar --exclude=.venv --exclude=instance --exclude=.git --exclude=__pycache__ -czf ~/print-server-backup-before-release/source.tar.gz .
cp ~/.config/systemd/user/print-server.service ~/.config/systemd/user/print-cleanup.service ~/.config/systemd/user/print-cleanup.timer ~/print-server-backup-before-release/
```

Back up SQLite consistently (with services stopped):

```bash
python -c 'import sqlite3; from pathlib import Path; s=sqlite3.connect("instance/print-server.sqlite3"); d=sqlite3.connect(Path.home()/"print-server-backup-before-release/history.sqlite3"); s.backup(d); d.close(); s.close()'
```

The backup contains historical filenames; keep it private. Documents are intentionally not backed up.

## 3. Copy the release files

```bash
cp ~/print-server-staging/print-server-release/*.py .
cp ~/print-server-staging/print-server-release/requirements.txt .
cp ~/print-server-staging/print-server-release/README.md .
cp -r ~/print-server-staging/print-server-release/templates .
cp -r ~/print-server-staging/print-server-release/static .
cp -r ~/print-server-staging/print-server-release/tests .
cp -r ~/print-server-staging/print-server-release/docs .
cp -r ~/print-server-staging/print-server-release/systemd .
```

Keep your existing `.gitignore`; ensure it excludes `instance/`, `.venv/`, `__pycache__/`, `.env`, databases and uploaded PDFs. A sample is in staging. Old migration scripts can remain, but use the new `init_db.py` for future setup.

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python init_db.py
python -m unittest discover -s tests -v
python -m pip freeze > requirements.lock.txt
```

`init_db.py` adds missing columns and a unique submission-token index, keeps historical rows, and creates a persistent private session-signing key. Never commit or publish `instance/secret.key`. Do not change it on each startup.

The PDF page count for validating/rejected rows is temporarily 1 to remain compatible with the original table's positive-page-count constraint; only accepted PDFs have a validated count. The result page hides that placeholder for rejected jobs.

If installation or tests fail, keep services stopped and inspect the error rather than continuing.

## 4. Install services and start

```bash
cp systemd/print-server.service ~/.config/systemd/user/
cp systemd/print-cleanup.service ~/.config/systemd/user/
cp systemd/print-cleanup.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now print-server.service print-cleanup.timer
systemctl --user status print-server.service --no-pager
systemctl --user list-timers print-cleanup.timer
```

Linger was already enabled for `pritilend`; verify using `loginctl show-user pritilend -p Linger`. No new firewall rules are required.

Open the SSH tunnel from Windows if needed:

```powershell
ssh -N -L 127.0.0.1:5000:127.0.0.1:5000 pritilend@192.168.0.21
```

Open http://127.0.0.1:5000 in that Windows browser. The explicit local bind keeps the tunnel listener on Windows loopback as well.

## 5. Acceptance and rollback

Follow ACCEPTANCE.md. Do not claim this revision deployed until the real PDF, cleanup and reboot checks pass.

For rollback: stop the web service and timer; restore prior source and service files from the private backup; reload systemd; restart. The schema migration is additive, so prior code can generally read it. **Do not blindly restore the old database after new prints:** it would erase records of real submissions. Restore a DB only after reconciling all jobs with CUPS, and never automatically replay pending jobs. File deletion cannot be undone without a separate original document.
