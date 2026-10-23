"""Reconcile statuses and delete PDFs; never submit print jobs."""
import fcntl
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from common import INSTANCE, QUEUE, database, update, remove_upload


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def maintain(connection):
    # Called by tests with a fake CUPS connection as well as by the real timer.
    with database() as db:
        jobs = db.execute('SELECT * FROM print_jobs WHERE file_deleted_at IS NULL').fetchall()
    for job in jobs:
        job_id, state = job['id'], job['status']
        if state == 'completed':
            remove_upload(job_id)
            print(f'{job_id}: completed; upload copy removed')
            continue
        age = time.time() - datetime.strptime(job['created_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        if state in ('validating', 'submitting') and age < 300:
            continue  # Do not race an active request.
        if state == 'validating':
            update(job_id, status='rejected', error_message='Upload interrupted before submission.')
            remove_upload(job_id)
            continue
        if state == 'rejected':
            remove_upload(job_id)
            continue
        if not job['cups_job_id'] and state in ('submitting', 'needs_review'):
            candidates = connection.getJobs(which_jobs='all', my_jobs=True)
            matches = [number for number, attrs in candidates.items()
                       if job['cups_title'] and attrs.get('job-name') == job['cups_title']
                       and unquote(urlparse(attrs.get('job-printer-uri', '')).path).endswith('/' + QUEUE)]
            if len(matches) == 1:
                update(job_id, cups_job_id=matches[0], status='submitted', error_message=None)
                cups_id = matches[0]
            else:
                update(job_id, status='needs_review', error_message='Unable to establish submission outcome. Operator review required; do not resubmit.')
                continue
        else:
            cups_id = job['cups_job_id']
        if not cups_id:
            # Old 'saved' records must be investigated manually, never guessed.
            continue
        try:
            attrs = connection.getJobAttributes(cups_id)
        except Exception as error:
            print(f'{job_id}: CUPS lookup unavailable; keeping file ({type(error).__name__})')
            continue
        printer_path = unquote(
            urlparse(attrs.get("job-printer-uri", "")).path
        )
        actual_title = attrs.get("job-name")

        wrong_id = attrs.get("job-id") != cups_id
        wrong_printer = printer_path != f"/printers/{QUEUE}"
        wrong_title = (
            job["cups_title"] is not None
            and actual_title is not None
            and actual_title != job["cups_title"]
        )

        if wrong_id or wrong_printer or wrong_title:
            update(
                job_id,
                status="needs_review",
                error_message="CUPS job identity mismatch; operator review required.",
            )
            continue
        states = {3: 'queued', 4: 'held', 5: 'processing', 6: 'stopped',
                  7: 'canceled', 8: 'failed', 9: 'completed'}
        status = states.get(attrs.get('job-state'))
        if not status:
            continue
        changes = {'status': status, "error_message": None}
        if status in ('completed', 'canceled', 'failed'):
            finished = attrs.get('time-at-completed')
            terminal_at = job['terminal_at'] or utc(finished if isinstance(finished, int) and finished > 0 else time.time())
            changes['terminal_at'] = terminal_at
            if status == 'completed':
                changes['completed_at'] = terminal_at
        update(job_id, **changes)
        if status == 'completed':
            remove_upload(job_id)
            print(f'{job_id}: completed; upload copy removed')
        elif status in ('canceled', 'failed'):
            elapsed = time.time() - datetime.strptime(changes['terminal_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
            if elapsed >= 86400:
                remove_upload(job_id)
                print(f'{job_id}: terminal failure older than 24h; upload removed')


if __name__ == '__main__':
    import cups
    with (INSTANCE / 'cleanup.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)
        maintain(cups.Connection())
