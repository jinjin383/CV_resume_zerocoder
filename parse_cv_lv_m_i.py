#!/usr/bin/env python3
"""
scan_webpages.py – Extract visible text and OCR text inside images from a list of Web pages.
Supports Latvian (lav), Russian (rus) and English (eng).

Usage
-----
python scan_webpages.py URL [URL ...] [-o OUTPUT.json] [--markdown] [--md-file OUTPUT.md]

Dependencies
------------
* Python >=3.9
* pip install -U requests beautifulsoup4 pillow pytesseract langdetect tqdm rich
* Tesseract OCR engine with traineddata files for lav, rus, eng. On Debian/Ubuntu:
  sudo apt-get install tesseract-ocr tesseract-ocr-lav tesseract-ocr-rus tesseract-ocr-eng
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup, NavigableString, Comment
from langdetect import detect_langs
from PIL import Image
import pytesseract
from tqdm import tqdm

from rich.console import Console
from rich.markdown import Markdown


import requests
from bs4 import BeautifulSoup

def get_html(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text

def extract_vacancy_data(html):
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.find("div", class_="vacancy-description")
    if desc:
        return desc.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)

# Languages we care about (Tesseract + langdetect codes)
TARGET_LANGS = {
    "lav": "Latvian",
    "rus": "Russian",
    "eng": "English",
}

def is_visible_element(element: NavigableString | Comment) -> bool:
    parent = element.parent.name if element.parent else ""
    if parent in ("style", "script", "head", "title", "meta", "[document]"):
        return False
    if isinstance(element, Comment):
        return False
    text = str(element)
    if not text.strip():
        return False
    return True

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    texts = soup.find_all(string=True)
    visible_texts = filter(is_visible_element, texts)
    joined = " ".join(t.strip() for t in visible_texts)
    return re.sub(r"\s+", " ", joined)

def detect_relevant_langs(text: str) -> List[str]:
    try:
        langs = detect_langs(text)
    except Exception:
        return []
    return [l.lang for l in langs if l.lang in TARGET_LANGS]

def download_image(url: str, session: requests.Session, tmpdir: Path) -> Path | None:
    try:
        r = session.get(url, timeout=15, stream=True)
        r.raise_for_status()
        suffix = os.path.splitext(url.split("?")[0])[1][:5] or ".jpg"
        fp = tmpdir / f"img_{abs(hash(url))}{suffix}"
        with fp.open("wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return fp
    except Exception:
        return None

def ocr_image(fp: Path) -> str:
    try:
        img = Image.open(fp)
        gray = img.convert("L")
        return pytesseract.image_to_string(gray, lang="lav+rus+eng")
    except Exception:
        return ""

def scrape_page(url: str, session: requests.Session) -> Dict[str, Any]:
    page_data: Dict[str, Any] = {
        "url": url,
        "visible_text": "",
        "visible_text_langs": [],
        "images": [],  # list of dicts {src, ocr_text, ocr_langs}
    }
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        page_data["error"] = str(e)
        return page_data

    html = resp.text
    visible_text = extract_visible_text(html)
    page_data["visible_text"] = visible_text
    page_data["visible_text_langs"] = detect_relevant_langs(visible_text)

    soup = BeautifulSoup(html, "html.parser")
    img_tags = soup.find_all("img")
    if not img_tags:
        return page_data

    with tempfile.TemporaryDirectory() as dtmp:
        dtmp_path = Path(dtmp)
        for img in img_tags:
            src = img.get("src") or ""
            if not src:
                continue
            img_url = src if src.startswith("http") else requests.compat.urljoin(url, src)
            fp = download_image(img_url, session, dtmp_path)
            if not fp:
                continue
            ocr_text = ocr_image(fp)
            page_data["images"].append({
                "src": img_url,
                "ocr_text": ocr_text,
                "ocr_langs": detect_relevant_langs(ocr_text),
            })
    return page_data

def format_results_as_markdown(results: List[Dict[str, Any]]) -> str:
    lines = []
    for page in results:
        lines.append(f"# URL: {page.get('url', '')}\n")
        if "error" in page:
            lines.append(f"**Ошибка:** {page['error']}\n")
            continue
        lines.append("## Видимый текст\n")
        lines.append(f"{page.get('visible_text', '')}\n")
        langs = page.get('visible_text_langs', [])
        if langs:
            names = [TARGET_LANGS.get(l, l) for l in langs]
            lines.append(f"**Обнаруженные языки:** {', '.join(names)}\n")
        images = page.get('images', [])
        if images:
            lines.append("## Изображения с OCR\n")
            for img in images:
                lines.append(f"### Изображение: {img.get('src', '')}\n")
                lines.append(f"{img.get('ocr_text', '')}\n")
                ocr_langs = img.get('ocr_langs', [])
                if ocr_langs:
                    names = [TARGET_LANGS.get(l, l) for l in ocr_langs]
                    lines.append(f"**Языки OCR:** {', '.join(names)}\n")
    return "\n".join(lines)

def print_ocr_text_only(results: List[Dict[str, Any]]):
    # Вывод только текста из всех картинок (только вакансия, без метаданных)
    texts = []
    for page in results:
        if "images" in page:
            for img in page["images"]:
                text = img.get("ocr_text", "").strip()
                if text:
                    texts.append(text)
    print("\n\n".join(texts))  # Между вакансиями — 2 перевода строки

def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="Scan webpages for visible and OCR text in Latvian, Russian and English.")
    parser.add_argument("urls", nargs="+", help="Web page URLs to scan")
    parser.add_argument("-o", "--output", help="Write JSON results to this file instead of stdout")
    parser.add_argument("--markdown", action="store_true", help="Выводить результаты в формате Markdown в терминал")
    parser.add_argument("--md-file", help="Сохранить результаты в файл в формате Markdown")
    args = parser.parse_args(argv)

    session = requests.Session()
    results = []
    for url in tqdm(args.urls, desc="Scanning pages"):
        results.append(scrape_page(url, session))

    # ↓↓↓↓↓  Основное отличие ↓↓↓↓↓
    if args.markdown or args.md_file:
        md_output = format_results_as_markdown(results)
        if args.md_file:
            Path(args.md_file).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            with open(args.md_file, "w", encoding="utf-8") as f:
                f.write(md_output)
            print(f"Результаты сохранены в файл: {args.md_file}")
        if args.markdown:
            console = Console()
            console.print(Markdown(md_output))
    elif args.output:
        Path(args.output).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Результаты сохранены в файл: {args.output}")
    else:
        # ТОЛЬКО ДАННЫЕ О ВАКАНСИИ (текст из изображений)
        print_ocr_text_only(results)

if __name__ == "__main__":
    main()
