"""Deterministic browser checks using one fresh page per case and camera-state assertions."""
import os
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("TERRAIN_URL", "http://localhost:5174")
CHROME = os.environ.get("CHROME_PATH", "C:/Program Files/Google/Chrome/Application/chrome.exe")
PIPELINE_URL = os.environ.get("TERRAIN_PIPELINE_URL")

def launch(p):
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=["--enable-unsafe-swiftshader"], timeout=10000)
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" and ("THREE." in message.text or "WebGL" in message.text) else None)
    return browser, page, errors

def ready(page, path, canvases):
    page.goto(BASE + path, timeout=10000, wait_until="domcontentloaded")
    page.wait_for_function(f"document.querySelectorAll('canvas').length === {canvases}", timeout=15000)
    page.wait_for_timeout(700)

def set_range(locator, value):
    locator.evaluate("""(element, value) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(element, value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }""", value)

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
        # Repeating the same action must restore the view after orbiting away.
        for label in ["Reset Camera", "Top View", "Perspective View", "Fit Terrain"]:
            button = page.get_by_role("button", name=label)
            button.click(); page.wait_for_timeout(500)
            initial = state(page, key)
            drag(page, canvas, "right", 60, 20)
            button.click(); page.wait_for_timeout(500)
            restored = state(page, key)
            assert max(abs(a - b) for a, b in zip(initial["target"], restored["target"])) < 1e-3, label
        set_range(page.locator("input[aria-label='Vertical exaggeration']"), "2.0")
        assert page.locator("output").filter(has_text="2.0").count() == 1
        page.locator("input").first.fill("/terrain/moon_demo.json")
        page.get_by_text("Synthetic Moon surface with NoData", exact=True).first.wait_for()
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
        assert synced_right["position"] != right["position"]
        synced_left = state(page, left_key)
        assert max(abs(a - b) for a, b in zip(synced_left["position"] + synced_left["target"], synced_right["position"] + synced_right["target"])) < 1e-3
        drag(page, canvases.nth(1), "right", 40, 10); synced_left = state(page, left_key)
        assert synced_left["target"] != left["target"]
        sync.uncheck(); page.wait_for_timeout(1500); independent_before = state(page, left_key)
        drag(page, canvases.nth(1), "left", 60, 10); independent_after = state(page, left_key)
        assert max(abs(a - b) for a, b in zip(independent_after["position"] + independent_after["target"], independent_before["position"] + independent_before["target"])) < 1e-3
        mode = page.locator("select").nth(0); mode.select_option("relative")
        assert page.get_by_text("Shared relative elevation legend", exact=False).count() == 1
        mode.select_option("absolute")
        assert page.get_by_text("Shared relative elevation legend", exact=False).count() == 0
        set_range(page.locator("input[aria-label='Shared exaggeration']"), "2.5")
        assert page.locator("input[aria-label='Shared exaggeration']").input_value() == "2.5"
        assert page.get_by_text("synthetic", exact=False).count() > 0
        print("PASS isolated comparison bidirectional sync, independence, elevation modes, shared exaggeration, warnings", flush=True)
        # Large downward orbit and pan must keep the camera above the terrain.
        page.get_by_role("button", name="Reset Camera").first.click()
        drag(page, canvases.nth(0), "left", 0, -600)
        guarded = state(page, left_key)
        assert guarded["position"][1] > guarded["target"][1]
        drag(page, canvases.nth(0), "right", 0, 250)
        guarded = state(page, left_key)
        assert guarded["position"][1] > guarded["target"][1]
        page.get_by_role("button", name="Reset Camera").first.click()
        # Surface materials must compile, including the high-frequency detail layer.
        surface = page.get_by_role("combobox", name="Surface appearance")
        for appearance in ["Mars", "Moon", "Earth", "elevation", "neutral", "surface"]:
            surface.select_option(appearance); page.wait_for_timeout(200)
        page.get_by_role("button", name="Enter POV").first.click()
        dialog = page.get_by_role("dialog", name="Planet terrain explorer")
        dialog.wait_for(); page.wait_for_timeout(900)
        assert page.evaluate("document.body.style.overflow") == "hidden"
        pov = lambda: page.evaluate("window.__terrain3dPov")
        initial = pov(); assert initial["body"] == "Mars"
        pov_canvas = dialog.locator("canvas")
        drag(page, pov_canvas, "left", 95, 35)
        assert pov()["rotation"] != initial["rotation"]
        before_move = pov()["position"]
        page.keyboard.down("w"); page.wait_for_timeout(300); page.keyboard.up("w")
        assert pov()["position"] != before_move
        heading = pov()["heading"]
        for body in ["Earth", "Mars", "Moon", "Earth"]:
            dialog.get_by_role("navigation", name="POV destination").get_by_role("button", name=body, exact=True).click()
            page.wait_for_timeout(800)
            current = pov()
            assert current["body"] == body and all(isinstance(value, (int, float)) for value in current["position"])
            assert current["heading"] == heading
            assert dialog.get_by_role("button", name=body, exact=True).get_attribute("aria-pressed") == "true"
        assert pov()["view"] == "third"
        dialog.get_by_role("combobox", name="Explorer camera").select_option("first")
        page.wait_for_timeout(200); assert pov()["view"] == "first"
        dialog.get_by_role("combobox", name="Explorer camera").select_option("third")
        page.wait_for_timeout(200); assert pov()["view"] == "third"
        # Equal launch impulse: Moon has the highest peak and longest airtime.
        flights = []
        for body in ["Earth", "Mars", "Moon"]:
            dialog.get_by_role("navigation", name="POV destination").get_by_role("button", name=body, exact=True).click()
            page.wait_for_function("body => window.__terrain3dPov?.body === body && window.__terrain3dPov.grounded", arg=body)
            dialog.get_by_role("button", name="Return to parcel").click()
            dialog.get_by_role("button", name="Jump", exact=True).click()
            page.wait_for_function("window.__terrain3dPov?.grounded === false")
            # A second click in the air must not reset velocity or launch another jump.
            dialog.get_by_role("button", name="Jump", exact=True).click()
            flight = page.evaluate("""() => new Promise((resolve, reject) => {
                let peak = 0; const deadline = performance.now() + 15000;
                const sample = () => {
                    const s = window.__terrain3dPov;
                    peak = Math.max(peak, s.player[1] - s.ground);
                    if (s.grounded) return resolve({peak, elapsed: s.jumpElapsed, gravity: s.gravity});
                    if (performance.now() > deadline) return reject(new Error('Jump did not land'));
                    requestAnimationFrame(sample);
                }; sample();
            })""")
            assert flight["peak"] > 0
            assert abs(flight["elapsed"] - 7.2 / flight["gravity"]) < 0.15, flight
            flights.append(flight)
        assert flights[0]["peak"] < flights[1]["peak"] < flights[2]["peak"]
        assert flights[0]["elapsed"] < flights[1]["elapsed"] < flights[2]["elapsed"]
        # Space works from the terrain canvas; holding it must not bunny-hop on landing.
        dialog.get_by_role("button", name="Earth", exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.body === 'Earth' && window.__terrain3dPov.grounded")
        dialog.locator("canvas").focus()
        page.keyboard.down("Space")
        page.wait_for_function("!window.__terrain3dPov.grounded")
        page.keyboard.down("Space")
        page.wait_for_function("window.__terrain3dPov.grounded")
        page.wait_for_timeout(250)
        assert pov()["grounded"]
        page.keyboard.up("Space")
        # Reset and a world change cancel the old jump. Camera-mode changes preserve it.
        dialog.get_by_role("button", name="Jump", exact=True).click()
        page.wait_for_function("!window.__terrain3dPov.grounded")
        dialog.get_by_role("combobox", name="Explorer camera").select_option("first")
        assert not pov()["grounded"]
        dialog.get_by_role("button", name="Return to parcel").click()
        page.wait_for_function("window.__terrain3dPov.grounded && window.__terrain3dPov.verticalVelocity === 0")
        dialog.get_by_role("combobox", name="Explorer camera").select_option("third")
        dialog.get_by_role("button", name="Jump", exact=True).click()
        page.wait_for_function("!window.__terrain3dPov.grounded")
        dialog.get_by_role("button", name="Mars", exact=True).click()
        page.wait_for_function("window.__terrain3dPov.body === 'Mars' && window.__terrain3dPov.grounded")
        dialog.get_by_role("button", name="Earth", exact=True).click()
        page.wait_for_function("window.__terrain3dPov.body === 'Earth' && window.__terrain3dPov.grounded")
        print("PASS planet jump heights/airtimes, no double jump or auto-repeat, Space, first person, reset and planet-change landing", flush=True)
        dialog.get_by_role("combobox", name="POV travel speed").select_option("3")
        page.get_by_role("button", name="Return to parcel").focus()
        page.keyboard.down("Shift"); page.keyboard.down("s")
        page.wait_for_timeout(2200)
        location = pov()["location"]
        assert 0 <= location["u"] <= 1 and 0 <= location["v"] <= 1, location
        assert pov()["boundaryBlocked"], pov()
        # Trying to jump across the boundary still cannot move outside the parcel.
        dialog.get_by_role("button", name="Jump", exact=True).click()
        page.wait_for_timeout(250)
        location = pov()["location"]
        assert 0 <= location["u"] <= 1 and 0 <= location["v"] <= 1, location
        page.keyboard.up("s"); page.keyboard.up("Shift")
        dialog.get_by_role("button", name="Return to parcel").click()
        page.wait_for_timeout(300)
        location = pov()["location"]
        assert 0 <= location["u"] <= 1 and 0 <= location["v"] <= 1
        page.keyboard.press("Escape")
        assert page.get_by_role("dialog").count() == 0
        assert page.evaluate("document.body.style.overflow") != "hidden"
        assert page.get_by_role("button", name="Enter POV").first.evaluate("e => e === document.activeElement")
        # Touch-sized view, on-screen movement and clean exit/re-entry.
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Enter POV").nth(1).click()
        dialog = page.get_by_role("dialog"); page.wait_for_timeout(700)
        assert pov()["body"] == "Earth"
        before_move = pov()["position"]
        forward = dialog.get_by_role("button", name="Move forward")
        forward.hover(); page.mouse.down(); page.wait_for_timeout(250); page.mouse.up()
        assert pov()["position"] != before_move
        dialog.get_by_role("button", name="Jump", exact=True).click()
        page.wait_for_function("!window.__terrain3dPov.grounded")
        assert pov()["player"][1] > pov()["ground"]
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        dialog.get_by_role("button", name="Exit POV").click()
        assert page.get_by_role("dialog").count() == 0
        print("PASS surface shaders, third/first person, parcel containment while walking/jumping, parcel return, planet transitions, Escape/focus, mobile controls", flush=True)

    finally:
        assert not errors, errors
        browser.close()

    browser, page, errors = launch(p)
    try:
        ready(page, "", 2)
        selected = page.get_by_role("button", name="Focus selected parcel:").first
        selected.hover()
        assert selected.get_attribute("data-hovered") == "true"
        page.mouse.move(5, 5)
        page.wait_for_function("document.querySelector('.overview-parcel').dataset.hovered === 'false'")
        selected.focus()
        assert selected.get_attribute("data-hovered") == "true"
        selected.click()
        assert page.get_by_text("24 generated parcels · Decorative surroundings", exact=True).count() == 2
        # Actual terrain hover triggers the same highlight, without a DOM hit area over the mesh.
        selected.evaluate("e => e.blur()")
        box = page.locator("canvas").first.bounding_box()
        page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.55)
        page.wait_for_function("document.querySelector('.overview-parcel').dataset.hovered === 'true'")
        page.mouse.move(5, 5)
        page.wait_for_function("document.querySelector('.overview-parcel').dataset.hovered === 'false'")
        print("PASS overview selected-parcel hover, keyboard focus, refocus, surrounding context and shader rendering", flush=True)
        satellite = page.get_by_role("button", name="Inspect orbiting satellite").first
        satellite.focus(); page.keyboard.press("Enter")
        page.get_by_text("Greetings, Earthling. Nice parcel!", exact=True).wait_for()
        expect(satellite).to_have_attribute("aria-pressed", "true")
        page.wait_for_timeout(1100)
        page.get_by_role("button", name="Dismiss alien").click()
        assert page.get_by_text("Greetings, Earthling. Nice parcel!", exact=True).count() == 0
        satellite.click()
        page.get_by_text("Greetings, Earthling. Nice parcel!", exact=True).wait_for()
        satellite.click()
        assert page.get_by_text("Greetings, Earthling. Nice parcel!", exact=True).count() == 0
        print("PASS satellite keyboard/pointer activation, alien encounter, dismiss and repeat toggle", flush=True)

        assert page.get_by_text("Awaiting similarity engine data", exact=True).count() == 1
        assert page.get_by_text("Demonstration dataset", exact=True).count() == 1
        assert page.get_by_text("One or both datasets are synthetic", exact=False).count() == 1
        print("PASS compact summaries, collapsed scientific details, camera toolbar, similarity empty state, synthetic warning", flush=True)
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
