import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "execution"))

from server import ReportRequestHandler  # noqa: E402


class handler(ReportRequestHandler):
    pass
