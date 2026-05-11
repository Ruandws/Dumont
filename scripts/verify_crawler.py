"""
Script de verificação do crawler.
Executa o crawler em 1 página e salva os HTML snippets capturados
para inspeção manual.

Uso (a partir da raiz do projeto):
    python scripts/verify_crawler.py
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Garante que a raiz do projeto está no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.core.browser import get_browser_page, logger  # noqa: E402
from src.core.crawler import crawl  # noqa: E402

OUTPUT_DIR = ROOT / "scripts" / "_output"


async def main():
    search_url = os.getenv("SEARCH_URL")
    if not search_url:
        logger.error("SEARCH_URL não definida em .env")
        sys.exit(1)

    # Força crawl de apenas 1 página para teste rápido
    os.environ["MAX_PAGES"] = "1"

    logger.info(f"Verificando crawler com URL: {search_url}")

    async with get_browser_page() as page:
        ads = await crawl(page, search_url)

    if not ads:
        logger.warning("Nenhum anúncio capturado — verifique seletores ou bloqueios.")
        sys.exit(1)

    # Salva cada snippet para inspeção
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines = []
    for i, (url, html) in enumerate(ads, 1):
        filename = OUTPUT_DIR / f"ad_{i:03d}.html"
        filename.write_text(html, encoding="utf-8")

        # Diagnóstico rápido
        has_price = "R$" in html or "price" in html.lower()
        has_title = "<h2" in html.lower() or "adcard" in html.lower()
        has_img = "<img" in html.lower()
        char_count = len(html)

        status = "OK" if (has_price and char_count > 200) else "??"
        summary_lines.append(
            f"  {status} Ad {i:03d}: {char_count:>6} chars | "
            f"price={'Y' if has_price else 'N'}  "
            f"title={'Y' if has_title else 'N'}  "
            f"img={'Y' if has_img else 'N'} | "
            f"{url[:80]}"
        )

    # Relatório
    print("\n" + "=" * 70)
    print("  RELATÓRIO DE VERIFICAÇÃO DO CRAWLER")
    print(f"  Total de anúncios capturados: {len(ads)}")
    print("=" * 70)
    for line in summary_lines:
        print(line)
    print("=" * 70)
    print(f"  HTML salvo em: {OUTPUT_DIR}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
