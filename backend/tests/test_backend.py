from pathlib import Path
import sys


def test_app_import_smoke():
    """Smoke test that the FastAPI app module imports and exposes `app`."""
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))
    try:
        from app import app
    finally:
        sys.path.pop(0)

    assert app is not None
