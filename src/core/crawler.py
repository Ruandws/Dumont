import os
import time
import random
from typing import List, Set, Optional, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from .browser import logger


def crawl(
    page: Page,
    search_url: str,
    existing_urls: Optional[Set[str]] = None,
) -> List[Tuple[str, str]]:
    """Navega pelas páginas da OLX e coleta pares (url, html_snippet).

    Returns:
        Lista de tuplas (url_do_anuncio, html_snippet) para o parser.
    """
    existing_urls = existing_urls or set()
    max_pages = int(os.getenv("MAX_PAGES", "3"))
    all_ads: List[Tuple[str, str]] = []

    for page_num in range(1, max_pages + 1):
        ads = _fetch_page(page, search_url, page_num)
        new_urls = [url for url, _ in ads if url not in existing_urls]
        all_ads.extend(ads)

        if not new_urls:
            logger.info(f"Early stop na página {page_num}: nenhum anúncio novo.")
            break

        if page_num < max_pages:
            time.sleep(random.uniform(2.0, 5.0))

    return all_ads


def _fetch_page(
    page: Page, base_url: str, page_num: int,
) -> List[Tuple[str, str]]:
    """Acessa uma página e retorna anúncios. Retry máx 2x para timeout/429."""
    url = f"{base_url}&o={page_num}" if page_num > 1 else base_url

    for attempt in range(1, 4):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            ads = _extract_ads(page, url)
            return ads
        except PlaywrightTimeout:
            if attempt <= 2:
                logger.warning(
                    f"Timeout na página {page_num}, retry {attempt}/2."
                )
                time.sleep(2)
            else:
                logger.warning(
                    f"Página {page_num} ignorada após 2 retries (timeout)."
                )
                return []
        except Exception as e:
            logger.error(f"Erro inesperado na página {page_num}: {e}")
            return []

    return []


def _extract_ads(
    page: Page, current_url: str,
) -> List[Tuple[str, str]]:
    """Extrai pares (url, html_snippet) dos cards de anúncio."""
    ads: List[Tuple[str, str]] = []
    elements = page.query_selector_all("a.olx-adcard__link")

    if not elements:
        logger.warning(f"Nenhum anúncio encontrado em {current_url}")
        return ads

    for el in elements:
        href = el.get_attribute("href")
        inner_html = el.evaluate("el => el.parentElement ? el.parentElement.innerHTML : null")
        if href and inner_html:
            ads.append((href, inner_html))

    return ads
