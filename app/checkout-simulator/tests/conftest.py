"""Make the app modules importable when pytest runs from the repo root."""
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Tests never touch Fabric.
os.environ.setdefault("APP_MODE", "mock")
