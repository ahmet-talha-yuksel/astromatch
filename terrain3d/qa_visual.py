from playwright.sync_api import sync_playwright
from pathlib import Path
import os

OUT = Path(__file__).parent / "qa-screens"
OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"), headless=True, args=["--enable-unsafe-swiftshader"])
    for width, height in [(1920, 1080), (1366, 768), (390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(os.environ.get("TERRAIN_URL", "http://localhost:5174"), wait_until="domcontentloaded", timeout=20000)
        page.wait_for_function("document.querySelectorAll('canvas').length === 2", timeout=20000)
        page.wait_for_timeout(900)
        metrics = page.evaluate("""() => ({
          viewport: [innerWidth, innerHeight],
          overflow: document.documentElement.scrollWidth > innerWidth,
          canvases: [...document.querySelectorAll('canvas')].map(e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; }),
          cards: [...document.querySelectorAll('.terrain-card')].map(e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; }),
          warnings: document.querySelectorAll('.comparison-warning').length,
          metadata: document.querySelectorAll('.terrain-metadata').length,
          headings: [...document.querySelectorAll('h1,h2')].map(e => e.textContent)
        })""")
        assert not metrics["overflow"], metrics
        print(metrics, flush=True)
        page.screenshot(path=str(OUT / f"terrain3d-{width}x{height}.png"), full_page=True)
        if width in (1366, 390):
            page.get_by_role("button", name="Enter POV").first.click()
            dialog = page.get_by_role("dialog", name="Planet terrain explorer")
            for body in (["Mars", "Earth", "Moon"] if width == 1366 else ["Earth", "Moon"]):
                dialog.get_by_role("navigation", name="POV destination").get_by_role("button", name=body, exact=True).click()
                page.wait_for_timeout(1000)
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
                page.screenshot(path=str(OUT / f"pov-{body.lower()}-{width}x{height}.png"))
            if width == 1366:
                dialog.get_by_role("button", name="Jump", exact=True).click()
                page.wait_for_timeout(1700)
                page.screenshot(path=str(OUT / "jump-moon-1366x768.png"))
            dialog.get_by_role("button", name="Exit POV").click()
        page.close()
    browser.close()
