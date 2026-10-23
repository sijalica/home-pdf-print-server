# Security design and limits

## Threat model

Protect document contents, printing resources and history from accidental duplication, malformed uploads, cross-site requests and unintended access by other local sessions. Intended users are trusted household members operating through an SSH login. The host administrator is trusted. A compromised host/account is outside the protections of this prototype.

| Concern | Implemented control | Remaining limitation |
|---|---|---|
| Unverified uploader | Mandatory self-reported name and clear disclosure | No accounts, passwords or MFA in the app; names can be impersonated |
| Network access | Loopback-only Gunicorn; explicit loopback SSH tunnel | SSH account controls access; direct LAN release not enabled |
| Forged browser POST | Signed expiring form bound to session; SameSite cookie | Not user authentication; malicious trusted users can submit directly |
| Duplicate print | Unique DB token, 303 redirect, no retry on uncertainty | New form means a new job; exactly-once physical printing is impossible to promise |
| PDF parser abuse | Separate process, CPU/memory/time limits, 100-page cap | Not a full OS sandbox; valid PDFs are not necessarily safe |
| Storage/resource exhaustion | 20 MiB total request, 20 outstanding jobs, 1 GiB free-space floor | CUPS spool and history can grow; trusted household use only |
| File/path manipulation | UUID disk names, exclusive 0600 creation, private directory, symlink check | Local account owns app and files; not hostile-local-user isolation |
| SQL injection | Bound parameters | Database is accessible to its owning Unix user |
| Shell injection | lp arguments as list, no shell | CUPS and driver must remain patched |
| Filename XSS | Jinja autoescape, no inline scripts, restrictive CSP | Do not add unsafe HTML rendering or raw PDF serving |
| Result disclosure | Result lookup checks browser-session owner | Not multi-user account authorization; old results unavailable through web |
| Content retention | Prompt completion cleanup; CUPS PreserveJobFiles No | Outages delay cleanup; uncertain/legacy files require review; no secure erase |

## Explicit nonclaims

This is not an internet-facing service, hardened multi-tenant system or production authentication platform. The runtime is still the pritilend account, which also has administrative privileges available interactively. No root process or sudo command is needed by the app. Dedicated service-account separation is a future enhancement.

UFW is **inactive**. One SSH allowance was prepared for the home /24 subnet but the firewall was not enabled. No VLANs or isolated subnets have been implemented. Those facts must stay explicit in portfolio evidence.

The session cookie is not Secure because browser access is HTTP on loopback over SSH; it is HttpOnly and SameSite Strict. For a future HTTPS deployment, enable Secure cookies and configure trusted hosts, proxy trust and firewall rules deliberately. Do not simply bind to 0.0.0.0 and call the app secure.

## Future improvements

Dedicated unprivileged service user; authentication and MFA through an established identity provider; per-user quotas; general report/export tool; stronger PDF sandboxing; dependency audit/pinning; active firewall and VLAN design; HTTPS LAN access; structured security events. Do these as documented changes with tests, rather than retroactively claiming them.

## Sources consulted

- Flask security considerations: https://flask.palletsprojects.com/en/stable/web-security/
- Flask uploads: https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
- CUPS options: https://www.cups.org/doc/options.html
- CUPS retention configuration: https://www.cups.org/doc/man-cupsd.conf.html
- pycups project: https://github.com/OpenPrinting/pycups

Project-specific limits are design choices, not vendor guarantees.
