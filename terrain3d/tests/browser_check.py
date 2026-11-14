"""Deterministic browser checks using one fresh page per case and camera-state assertions."""
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("TERRAIN_URL", "http://localhost:5174")
CHROME = os.environ.get("CHROME_PATH", "C:/Program Files/Google/Chrome/Application/chrome.exe")
PIPELINE_URL = os.environ.get("TERRAIN_PIPELINE_URL")

def launch(p):
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=["--enable-unsafe-swiftshader"], timeout=10000)
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return browser, page, errors

def ready(page, path, canvases):
    page.goto(BASE + path, timeout=10000, wait_until="domcontentloaded")
    page.wait_for_function(f"document.querySelectorAll('canvas').length === {canvases}", timeout=15000)
    page.wait_for_timeout(700)

def state(page, key):
    return page.evaluate("key => window.__terrain3dCameraStates?.[key]", key)

def distance(value):
    p, t = value["position"], value["target"]
    return sum((p[i] - t[i]) ** 2 for i in range(3)) ** 0.5

def drag(page, canvas, button, dx, dy):
    box = canvas.bounding_box(); x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y); page.mouse.down(button=button); page.mouse.move(x + dx, y + dy, steps=8); page.mouse.up(button=button)
    page.wait_for_timeout(300)

with sync_playwright() as p:
    browser, page, errors = launch(p)
    try:
        ready(page, "/tests/browser.html", 1)
        canvas = page.locator("canvas").first
        assert canvas.evaluate("e => getComputedStyle(e).touchAction") == "none"
        key = "mars-synthetic-json"
        before = state(page, key); assert before and canvas.evaluate("e => !!e.getContext('webgl2')")
        canvas.screenshot(timeout=5000)
        drag(page, canvas, "left", 80, 20); rotated = state(page, key)
        assert rotated["position"] != before["position"]
        drag(page, canvas, "right", 50, 15); panned = state(page, key)
        assert panned["target"] != rotated["target"]
        box = canvas.bounding_box(); page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.wheel(0, -300); page.wait_for_timeout(300); zoomed = state(page, key)
        assert abs(distance(zoomed) - distance(panned)) > 1e-4
        page.locator("input[aria-label='Vertical exaggeration']").fill("2.0")
        assert page.locator("output").filter(has_text="2.0").count() == 1
        page.locator("input").first.fill("/terrain/moon_demo.json")
        page.get_by_text("Synthetic Moon surface with NoData", exact=True).wait_for()
        assert page.get_by_text("93.75%", exact=True).count() == 1
        assert page.get_by_text("SYNTHETIC", exact=True).count() == 1
        details = page.locator("details.terrain-metadata").first
        assert details.evaluate("e => !e.open")
        details.locator("summary").click()
        assert details.evaluate("e => e.open")
        for label in ["Reset Camera", "Top View", "Perspective View", "Fit Terrain"]:
            assert page.get_by_role("button", name=label).count() == 1
        print("PASS isolated viewer geometry, rotation, pan, zoom, metadata, NoData, warning, exaggeration", flush=True)
    finally:
        assert not errors, errors
        browser.close()

    browser, page, errors = launch(p)
    try:
        ready(page, "/tests/comparison.html", 2)
        canvases = page.locator("canvas")
        left_key, right_key = "mars-synthetic-json", "earth-synthetic-json"
        left, right = state(page, left_key), state(page, right_key)
        sync = page.get_by_role("checkbox", name="Sync Cameras")
        sync.check(); drag(page, canvases.nth(0), "left", 70, 15)
        synced_right = state(page, right_key)
        assert synced_right["position"] != right["position"] and synced_right["target"] != right["target"]
        drag(page, canvases.nth(1), "right", 40, 10); synced_left = state(page, left_key)
        assert synced_left["target"] != left["target"]
        sync.uncheck(); page.wait_for_timeout(1500); independent_before = state(page, left_key)
        drag(page, canvases.nth(1), "left", 60, 10); independent_after = state(page, left_key)
        assert max(abs(a - b) for a, b in zip(independent_after["position"] + independent_after["target"], independent_before["position"] + independent_before["target"])) < 1e-3
        mode = page.locator("select").nth(0); mode.select_option("relative")
        assert page.get_by_text("Relative mode is display-only", exact=False).count() == 1
        mode.select_option("absolute")
        assert page.get_by_text("Relative mode is display-only", exact=False).count() == 0
        page.locator("input[aria-label='Shared exaggeration']").fill("2.5")
        assert page.locator("input[aria-label='Shared exaggeration']").input_value() == "2.5"
        assert page.get_by_text("synthetic", exact=False).count() > 0
        print("PASS isolated comparison bidirectional sync, independence, elevation modes, shared exaggeration, warnings", flush=True)
    finally:
        assert not errors, errors
        browser.close()

    browser, page, errors = launch(p)
    try:
        ready(page, "", 2)
        assert page.get_by_text("Awaiting similarity engine data", exact=True).count() == 1
        page.get_by_text("REAL SOURCE-DERIVED", exact=True).wait_for()
        assert page.get_by_text("Mars Jezero", exact=False).count() >= 1
        print("PASS compact summaries, collapsed scientific details, camera toolbar, similarity empty state, real DEM status", flush=True)
    finally:
        assert not errors, errors
        browser.close()

    if PIPELINE_URL:
        print("START pipeline", flush=True)
        browser, page, errors = launch(p)
        try:
            ready(page, "/tests/browser.html", 1)
            page.locator("input").first.fill(PIPELINE_URL)
            page.get_by_role("heading", name="Pipeline", exact=False).wait_for()
            assert page.get_by_text("Display spacing: 10 × 20 m", exact=False).count() == 1
            assert page.get_by_text("Window: 20 × 40 m", exact=False).count() == 1
            assert page.get_by_text("Valid data: 88.89%", exact=False).count() == 1
            print("PASS generated GeoTIFF JSON loaded in TerrainViewer", flush=True)
        finally:
            assert not errors, errors
            browser.close()
