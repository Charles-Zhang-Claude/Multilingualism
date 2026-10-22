"""Screenshot pages of the local preview (or any base URL) for review.
Usage: python3 pipeline/shots.py <base url> <out dir> path[|width[|dark]] ...
"""
import sys, asyncio
from playwright.async_api import async_playwright

base, out = sys.argv[1].rstrip("/"), sys.argv[2]


async def main():
    async with async_playwright() as p:
        import os
        px = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        b = await p.chromium.launch(proxy={"server": px} if px and not base.startswith("http://127.") else None)
        for spec in sys.argv[3:]:
            parts = spec.split("|")
            path, width = parts[0], int(parts[1]) if len(parts) > 1 else 1280
            dark = len(parts) > 2 and parts[2] == "dark"
            ctx = await b.new_context(ignore_https_errors=True, viewport={"width": width, "height": 900}, color_scheme="dark" if dark else "light",
                                      device_scale_factor=1)
            page = await ctx.new_page()
            errs = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(str(e)))
            await page.goto(base + path, wait_until="load", timeout=90000)
            await page.wait_for_timeout(4000)
            name = (path.strip("/").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-") or "home") + f"_{width}{'_dark' if dark else ''}.png"
            await page.screenshot(path=f"{out}/{name}", full_page=False)
            print(name, "errors:", errs[:3])
            await ctx.close()
        await b.close()

asyncio.run(main())
