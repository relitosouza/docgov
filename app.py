import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "execution"))

from server import ReportRequestHandler as handler  # noqa: E402, F401
