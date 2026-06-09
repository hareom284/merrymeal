"""Shared pytest fixtures for ai_assistant tests.

Django's default cache backend (LocMemCache) is process-global, so a
rate-limit counter set in one test silently leaks into the next file's
tests. Auto-clearing the cache between tests keeps every assertion
independent without each test file having to remember to do it.
"""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _isolate_cache_per_test():
    cache.clear()
    yield
    cache.clear()
