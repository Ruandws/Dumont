import logging
import random
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from playwright_stealth import Stealth
from playwright.async_api import async_playwright, Page, ViewportSize

logger = logging.getLogger("dumont")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) "
    "Gecko/20100101 Firefox/120.0",
]

VIEWPORTS: list[ViewportSize] = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]


@asynccontextmanager
async def get_browser_page() -> AsyncGenerator[Page, None]:
    """Inicia Playwright com stealth e User-Agent rotativo."""
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True)
            user_agent = random.choice(USER_AGENTS)
            
            context = await browser.new_context(
                user_agent=user_agent,
                viewport=random.choice(VIEWPORTS),
                device_scale_factor=1.0,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                color_scheme="light"
            )
            page = await context.new_page()
            
            # Aplica stealth no contexto conforme solicitado
            await Stealth().apply_stealth_async(context)
            
            logger.info(f"Browser iniciado com stealth (UA: {user_agent[:40]}...)")
            yield page
        except Exception as e:
            logger.error(f"Falha ao iniciar browser: {e}")
            raise
        finally:
            if browser:
                await browser.close()
