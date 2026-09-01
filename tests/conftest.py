import os

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-secret")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "")

import pytest

from app.core.cache import cache


@pytest.fixture(autouse=True)
def _reset_inference_cache():
    """app.core.cache.cache es un singleton de proceso (correcto para produccion,
    una sola base de datos por proceso). En tests, cada archivo crea su propia
    base de datos SQLite aislada, pero todas comparten ese mismo singleton -
    sin este reset, el cache de una prueba se filtraria a otra prueba con una
    base de datos completamente distinta."""
    cache.invalidate_all()
    yield
    cache.invalidate_all()
