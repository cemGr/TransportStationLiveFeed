import os
import re
from pathlib import Path
from filelock import FileLock, Timeout

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.bikemetro.constants import DATA_PAGE, HEADERS, TIMEOUT


def get_soup(session: requests.Session) -> BeautifulSoup:
    html = session.get(DATA_PAGE, headers=HEADERS, timeout=TIMEOUT).text
    return BeautifulSoup(html, "html.parser")

def first_href(soup: BeautifulSoup, pattern: str) -> str | None:
    link = soup.find("a", string=lambda t: t and re.search(pattern, t, re.I))
    return link["href"] if link else None

def stream_download(url: str, dest: Path, session: requests.Session) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        return dest

    part = dest.with_suffix(dest.suffix + ".part")
    lock = FileLock(str(part) + ".lock")

    try:
        with lock.acquire(timeout=60):
            if dest.exists():
                return dest

            bytes_done = part.stat().st_size if part.exists() else 0

            headers = {"Range": f"bytes={bytes_done}-"} if bytes_done else {}
            with session.get(url, stream=True, timeout=TIMEOUT, headers=headers) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0)) + bytes_done

                mode = "ab" if bytes_done else "wb"
                with open(part, mode) as fh, tqdm(
                    total=total,
                    initial=bytes_done,
                    unit="B",
                    unit_scale=True,
                    desc=dest.name,
                ) as bar:
                    for chunk in r.iter_content(1 << 15):
                        fh.write(chunk)
                        bar.update(len(chunk))

            os.replace(part, dest)

    except Timeout:
        raise RuntimeError(f"Could not obtain download lock for {dest}")

    finally:
        if lock.is_locked:
            lock.release()

    return dest