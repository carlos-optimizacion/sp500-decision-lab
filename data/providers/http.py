"""Cliente HTTP mínimo, reproducible y sin dependencia de requests."""

from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DataDownloadError(RuntimeError):
    pass


def fetch_bytes(url: str, timeout: int = 45, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 DecisionLab/0.2 educational-research",
                    "Accept": "application/json,text/csv,*/*",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.6 * (2**attempt))
    raise DataDownloadError(f"No se pudo descargar {url}: {last_error}") from last_error

