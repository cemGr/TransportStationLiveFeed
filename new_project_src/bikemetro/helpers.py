import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from new_project_src.bikemetro.constants import DATA_PAGE, HEADERS, TIMEOUT


# --- public façade -----------------------------------------------------------
def get_soup(session: requests.Session) -> BeautifulSoup:
    html = session.get(DATA_PAGE, headers=HEADERS, timeout=TIMEOUT).text
    return BeautifulSoup(html, "html.parser")

def first_href(soup: BeautifulSoup, pattern: str) -> str | None:
    link = soup.find("a", string=lambda t: t and re.search(pattern, t, re.I))
    return link["href"] if link else None

def stream_download(url: str, dest: Path, session: requests.Session) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in r.iter_content(1 << 15):
                f.write(chunk)
                bar.update(len(chunk))
        tmp.rename(dest)
    return dest
