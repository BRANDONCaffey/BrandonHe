from __future__ import annotations


def fetch_html(url: str, timeout_seconds: int = 20) -> str:
    try:
        from scrapling.fetchers import Fetcher  # type: ignore
    except Exception as exc:  # pragma: no cover - import-path guard
        raise RuntimeError("scrapling is not available; install dependency first") from exc

    try:
        page = Fetcher.get(url, timeout=timeout_seconds)
    except TypeError:
        page = Fetcher.get(url)

    for attr in ("html", "content"):
        value = getattr(page, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    text = str(page)
    if text.strip():
        return text
    raise RuntimeError(f"empty response body from scrapling for url={url}")
