"""Smoke tests for the local dev runner module."""


def test_run_module_imports() -> None:
    import run  # noqa: F401 — ensures module loads without executing __main__

    assert hasattr(run, "__name__")
