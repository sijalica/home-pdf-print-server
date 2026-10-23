# Home PDF Print Server

A small Linux home lab that gives a USB-only HP LaserJet P1102 a browser upload workflow through an SSH tunnel. Built while learning Python, Linux services, printing protocols and security boundaries.

**Status:** replacement release prepared and tested locally with a simulated printer. The earlier version physically printed on the Toshiba; deployment and reboot acceptance of this revision remain pending. This is a household lab, not a public print service.

Access currently uses an SSH tunnel. UFW remains inactive; direct LAN
access, network segmentation, application authentication, and MFA
are not implemented.

## What it does

- Accepts a self-reported name and one PDF; prints one copy of all pages.
- Validates PDFs in a subprocess with memory, CPU and wall-clock limits.
- Stores documents under generated IDs in a private directory.
- Records metadata and CUPS job ID in SQLite using parameterized SQL.
- Makes a repeated submission with the same form token return the same job rather than printing again.
- Redirects POST to a result page so a normal refresh does not resubmit.
- Polls CUPS every 15 seconds. Removes completed uploads promptly while retaining metadata.
- Records canceled and aborted jobs; retains their upload copy for 24 hours before removal.
- Preserves uncertain jobs for operator review. Never automatically resubmits to CUPS.
- Runs Gunicorn and cleanup as user systemd services.

## Deliberate scope

There is no web history listing: reporting is deferred to a later command-line exercise. Names are not verified accounts. Results are restricted to the browser session that submitted the job, which is convenience access control, not user authentication. No MFA, VLAN segmentation or active host firewall is claimed. Access stays on loopback through SSH; direct LAN access is deferred.

## Hardware baseline

Toshiba C50D-A-10U; Linux Mint 22.1 Xfce; 4 GB RAM and HDD; Wi-Fi; HP LaserJet P1102 over USB. CUPS/HPLIP/plugin already installed and printing. Queue: `HP_LaserJet_Professional_P1102`.

## Start here

1. Read [UPGRADE.md](docs/UPGRADE.md) to preserve the existing database and working deployment.
2. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [SECURITY.md](docs/SECURITY.md).
3. Run the tests: `python -m unittest discover -s tests -v`.
4. Complete [ACCEPTANCE.md](docs/ACCEPTANCE.md) on the Toshiba.
5. Use [OPERATIONS.md](docs/OPERATIONS.md) for routine management.

## Repository layout

| File | Purpose |
|---|---|
| app.py | HTTP routes, signed forms, durable duplicate prevention, submission |
| common.py | Shared database operations and private paths |
| init_db.py | Repeatable, additive schema migration; preserves existing jobs |
| validate_pdf.py | PDF inspection in a resource-limited process |
| cleanup_completed.py | Status reconciliation and deletion; never prints |
| templates/ and static/ | Upload, result and error pages; no JavaScript required |
| systemd/ | User web service, maintenance service and timer |
| tests/ | Temporary database and fake printer tests; no hardware printing |
| docs/ | Setup, security decisions, operations, acceptance and portfolio guide |

## Development

Python 3.12. Use a virtual environment. `requirements.txt` contains compatible version ranges, not a reproducible lock. After successful installation and testing on the Toshiba, save its exact versions to `requirements.lock.txt` with `python -m pip freeze > requirements.lock.txt` and commit that file. Review updates rather than blindly applying them.

The configuration and DB must exist before importing the web app: run `python init_db.py` first. Start with `python -m gunicorn --bind 127.0.0.1:5000 --workers 1 --threads 2 --timeout 75 app:app`. Do not run real-upload integration tests unless a physical print is intended.

## Portfolio summary

Built a Python/Flask print service for a legacy USB printer on Linux, with SQLite job history, CUPS integration, systemd operation, bounded PDF inspection, duplicate-submission protection, and automatic document retention controls. Documented trust boundaries, failure recovery, and remaining authentication and network-isolation limitations.

Use this description only after installing and validating this revision. The evidence guide separates earlier hardware results from newly automated tests.
