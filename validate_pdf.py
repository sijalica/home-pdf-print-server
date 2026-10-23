"""Isolated, resource-bounded PDF inspection. Linux only."""
import json
import resource
import sys

resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
from pypdf import PdfReader

try:
    reader = PdfReader(sys.argv[1], strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported.')
    pages = len(reader.pages)
    if not 1 <= pages <= 100:
        raise ValueError('PDF must have between 1 and 100 pages.')
    print(json.dumps({'pages': pages}))
except Exception:
    # File content is untrusted; detailed parser errors stay out of responses.
    print(json.dumps({'error': 'Unreadable, encrypted, or unsupported PDF.'}))
    sys.exit(1)
