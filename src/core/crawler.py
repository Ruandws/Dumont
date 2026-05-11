import os
import asyncio
import random
from typing import List, Set, Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from .browser import logger


async def crawl(
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
        ads = await _fetch_page(page, search_url, page_num)
        
        if ads is None:
            continue

        new_urls = [url for url, _ in ads if url not in existing_urls]
        all_ads.extend((url, html) for url, html in ads if url not in existing_urls)

        if not new_urls:
            logger.info(f"Early stop na página {page_num}: nenhum anúncio novo.")
            break

        if page_num < max_pages:
            # Mantém o delay original além do human_delay para maior jitter
            await asyncio.sleep(random.uniform(2.0, 5.0))

    return all_ads


def _build_url(base_url: str, page_num: int) -> str:
    """Constrói a URL da página com base no número da página."""
    return f"{base_url}&o={page_num}" if page_num > 1 else base_url


async def _handle_rate_limit(attempt: int) -> bool:
    """Lida com status 429 (Rate Limit). Retorna True se deve tentar novamente."""
    logger.warning("Rate limit (429) detectado!")
    if attempt <= 2:
        await asyncio.sleep(10 * attempt)
        return True
    return False


async def _handle_timeout(page_num: int, attempt: int) -> bool:
    """Lida com erro de timeout. Retorna True se deve tentar novamente."""
    if attempt <= 2:
        logger.warning(f"Timeout na página {page_num}, retry {attempt}/2.")
        await asyncio.sleep(2)
        return True
    logger.warning(f"Página {page_num} ignorada após 2 retries (timeout).")
    return False


async def _fetch_page(
    page: Page, base_url: str, page_num: int,
) -> Optional[List[Tuple[str, str]]]:
    """Acessa uma página e retorna anúncios. Retorna None em erro persistente."""
    url = _build_url(base_url, page_num)

    for attempt in range(1, 4):
        try:
            response = await page.goto(url, timeout=30000)
            
            if response and response.status == 429:
                if await _handle_rate_limit(attempt):
                    continue
                return None

            await page.wait_for_selector("section.olx-adcard", timeout=15000)
            return await _extract_ads(page, url)
        except PlaywrightTimeout:
            if await _handle_timeout(page_num, attempt):
                continue
            return None
        except Exception as e:
            logger.error(f"Erro inesperado na página {page_num}: {e}")
            return None

    return None


async def _extract_ads(
    page: Page, current_url: str,
) -> List[Tuple[str, str]]:
    """Extrai pares (url, html_snippet) dos cards de anúncio."""
    ads: List[Tuple[str, str]] = []
    sections = await page.query_selector_all("section.olx-adcard")

    if not sections:
        logger.warning(f"Nenhum anúncio encontrado em {current_url}")
        return ads

    for section in sections:
        link = await section.query_selector("a.olx-adcard__link")
        if not link:
            continue
        href = await link.get_attribute("href")
        inner_html = await section.evaluate("el => el.innerHTML")
        if href and inner_html:
            ads.append((href, inner_html))

    return ads
