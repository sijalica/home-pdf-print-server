import io
import os
import re
import tempfile
import unittest
import subprocess
from unittest.mock import patch

sandbox = tempfile.TemporaryDirectory()
os.environ['PRINT_INSTANCE'] = sandbox.name
import common
common.initialize()
from app import app
from cleanup_completed import maintain
from pypdf import PdfWriter


def pdf_bytes():
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(output)
    return output.getvalue()


class FlowTests(unittest.TestCase):
    def setUp(self):
        with common.database() as db:
            db.execute('DELETE FROM print_jobs')
        for path in common.UPLOADS.glob('*.pdf'):
            path.unlink()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.calls = 0
        self.real_run = subprocess.run

    def token(self):
        response = self.client.get('/')
        return re.search(rb'name="token" value="([^"]+)"', response.data).group(1).decode()

    def runner(self, arguments, **kwargs):
        if arguments[0] == 'lp':
            self.calls += 1
            return subprocess.CompletedProcess(arguments, 0, f'request id is {common.QUEUE}-42 (1 file(s))\n', '')
        return self.real_run(arguments, **kwargs)

    def submit(self, token=None, data=None, name='test.pdf'):
        return self.client.post('/upload', data={
            'token': token or self.token(), 'submitted_by': 'Test user',
            'document': (io.BytesIO(pdf_bytes() if data is None else data), name),
        })

    def row(self):
        with common.database() as db:
            return db.execute('SELECT * FROM print_jobs').fetchone()

    def test_valid_submission_and_refresh(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            response = self.submit()
            self.assertEqual(response.status_code, 303)
            self.assertEqual(self.client.get(response.location).status_code, 200)
            self.assertEqual(self.client.get(response.location).status_code, 200)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.row()['cups_job_id'], 42)

    def test_duplicate_token_only_prints_once(self):
        token = self.token()
        with patch('app.subprocess.run', side_effect=self.runner):
            first = self.submit(token)
            second = self.submit(token)
        self.assertEqual(first.location, second.location)
        self.assertEqual(self.calls, 1)

    def test_invalid_pdf_rejected_removed(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            self.submit(data=b'not PDF')
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.row()['status'], 'rejected')
        self.assertFalse(list(common.UPLOADS.glob('*.pdf')))

    def test_missing_token_blocked(self):
        self.assertEqual(self.client.post('/upload', data={'submitted_by': 'Test'}).status_code, 400)

    def test_other_session_cannot_view(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            response = self.submit()
        self.assertEqual(app.test_client().get(response.location).status_code, 404)

    def test_filename_not_used_as_path_or_html(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            response = self.submit(name='../../<script>alert(1)</script>.pdf')
        body = self.client.get(response.location).data
        self.assertNotIn(b'<script>', body)
        self.assertEqual(len(list(common.UPLOADS.glob('*.pdf'))), 1)

    def test_submission_timeout_not_retried(self):
        def timeout(args, **kwargs):
            if args[0] == 'lp':
                self.calls += 1
                raise subprocess.TimeoutExpired(args, 30)
            return self.real_run(args, **kwargs)
        token = self.token()
        with patch('app.subprocess.run', side_effect=timeout):
            self.submit(token)
            self.submit(token)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.row()['status'], 'needs_review')

    def test_cleanup_completion_retains_history(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            self.submit()
        row = self.row()
        class Cups:
            def getJobAttributes(self, number):
                return {
                    "job-id": number,
                    "job-printer-uri": (
                        f"ipp://localhost/printers/{common.QUEUE}"
                    ),
                    "job-state": 9,
                    "time-at-completed": 1800000000,
                }
        maintain(Cups())
        maintain(Cups())
        self.assertEqual(self.row()['status'], 'completed')
        self.assertIsNotNone(self.row()['file_deleted_at'])
        self.assertFalse(list(common.UPLOADS.glob('*.pdf')))

    def test_unknown_job_keeps_file(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            self.submit()
        class Cups:
            def getJobAttributes(self, number):
                raise RuntimeError('not found')
        maintain(Cups())
        self.assertTrue(list(common.UPLOADS.glob('*.pdf')))
        self.assertIsNone(self.row()['file_deleted_at'])

    def test_migration_preserves_history(self):
        with patch('app.subprocess.run', side_effect=self.runner):
            self.submit()
        before = self.row()['id']
        common.initialize()
        self.assertEqual(self.row()['id'], before)
    def test_wrong_printer_keeps_file(self):
        with patch("app.subprocess.run", side_effect=self.runner):
            self.submit()

        class Cups:
            def getJobAttributes(self, number):
                return {
                    "job-id": number,
                    "job-printer-uri": "ipp://localhost/printers/OTHER",
                    "job-state": 9,
                }

        maintain(Cups())

        self.assertEqual(self.row()["status"], "needs_review")
        self.assertIsNone(self.row()["file_deleted_at"])
        self.assertTrue(list(common.UPLOADS.glob("*.pdf")))

if __name__ == '__main__':
    unittest.main()
