# Portfolio preparation

Suggested repository name: home-pdf-print-server.

## Story

Problem: a USB-only printer required a nearby computer and manual file handling. Solution: reuse an older Linux laptop to receive PDF uploads over an encrypted SSH tunnel, submit to CUPS, retain metadata and remove completed documents.

Explain what was learned: Python/Flask from a Java background, Unix permissions, CUPS/IPP states, SQLite transactions, subprocess boundaries, systemd services/timers, and the distinction between reported completion and physical output.

## What makes the security work demonstrable

Show a malformed PDF rejected; a duplicate token causing only one simulated printer invocation; a result denied to a different browser session; cleanup preserving metadata; and uncertain submission remaining reviewable without automatic replay. Cite the tests and actual results rather than simply claiming “secure.”

## Publish checklist

- [ ] Deployment and hardware acceptance checklist completed or explicitly marked pending.
- [ ] Working changes reviewed with git diff and committed.
- [ ] .gitignore excludes instance, uploaded PDFs, virtualenv and secrets.
- [ ] Review all Git-tracked files with `git ls-files` before publishing.
- [ ] No personal filenames, emails, IP screenshots, credentials or live database in evidence.
- [ ] README status accurately reflects tested hardware and untested features.
- [ ] Choose a license deliberately; no license has been selected in this package.
- [ ] Publish only after your own final review; no repository was created or published automatically.

## Suggested demo (3 minutes)

1. Explain topology and the self-reported-name limitation.
2. Upload one sample PDF; show result and physical page.
3. Refresh result after maintenance; show deletion and retained history.
4. Explain one duplicate-submission test and one uncertainty test.
5. Show service/timer status and name remaining authentication/network work.

## Follow-on lab

Firewall and VLAN/subnet segmentation are a separate learning project. One firewall can enforce policies between multiple subnets. Plan assets and trust zones, diagram flows, define allow rules, test isolation and preserve management access. No firewall changes are included here.
