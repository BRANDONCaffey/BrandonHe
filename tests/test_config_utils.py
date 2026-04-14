from __future__ import annotations

from apps.api.config import as_float


def test_as_float_filters_non_finite_values():
    assert as_float(float('nan')) is None
    assert as_float(float('inf')) is None
    assert as_float(float('-inf')) is None


def test_as_float_parses_valid_values():
    assert as_float(1) == 1.0
    assert as_float('2.5') == 2.5
    assert as_float(' 3 ') == 3.0
