"""Exercise vehicle controls through actual keyboard/touch input and WebGL rendering."""
import os
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get('TERRAIN_URL', 'http://127.0.0.1:5174')
CHROME = os.environ.get('CHROME_PATH')
OUT = Path(os.environ.get('VEHICLE_SCREENSHOTS', '/tmp/astromatch-vehicles'))
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' and ('THREE.' in msg.text or 'WebGL' in msg.text) else None)
    try:
        page.goto(BASE + '/tests/vehicles.html', wait_until='domcontentloaded')
        page.get_by_role('button', name='Enter POV').first.click()
        dialog = page.get_by_role('dialog', name='Planet terrain explorer')
        page.wait_for_function("window.__terrain3dPov?.vehicle === 'astronaut'")
        pov = lambda: page.evaluate('window.__terrain3dPov')
        flight = lambda: page.evaluate('window.__terrain3dLanding')
        dialog.get_by_role('button', name='Rover', exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.vehicle === 'rover'")
        before = pov()['location']
        page.keyboard.down('w'); page.wait_for_timeout(400); page.keyboard.up('w')
        assert pov()['location'] != before
        dialog.get_by_role('button', name='Return to parcel', exact=True).click()
        dialog.get_by_role('button', name='Astronaut', exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.vehicle === 'astronaut'")
        page.keyboard.press('Space'); page.wait_for_function('!window.__terrain3dPov.grounded')
        dialog.get_by_role('button', name='Return to parcel', exact=True).click()
        page.wait_for_function('window.__terrain3dPov.grounded')
        print('PASS rover mode and return to astronaut jumping', flush=True)

        dialog.get_by_role('button', name='Pilot Voyager', exact=True).click()
        page.wait_for_function("window.__terrain3dLanding?.phase === 'ready'")
        initial = flight(); page.wait_for_timeout(300)
        assert flight()['y'] == initial['y']  # The pilot gets time to prepare.
        page.screenshot(path=str(OUT/'voyager-ready.png'))
        page.keyboard.down('Space'); page.wait_for_function('window.__terrain3dLanding.thrust')
        page.wait_for_timeout(150); page.keyboard.up('Space')
        page.wait_for_function("window.__terrain3dLanding?.phase === 'crashed'", timeout=20000)
        assert flight()['fuel'] < 100 and flight()['y'] >= flight()['ground']['height']
        assert dialog.get_by_text('Hard contact · Try again', exact=True).is_visible()
        dialog.get_by_role('button', name='Restart Voyager landing').click()
        page.wait_for_function("window.__terrain3dLanding?.phase === 'ready' && window.__terrain3dLanding.fuel === 100")
        dialog.get_by_role('button', name='Moon', exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.body === 'Moon' && !window.__terrain3dLanding")
        print('PASS manual activation, gravity-driven hard contact, restart, planet-change cancellation', flush=True)

        dialog.get_by_role('button', name='Pilot Voyager', exact=True).click()
        page.wait_for_function("window.__terrain3dLanding?.phase === 'ready'")
        page.keyboard.down('Space'); page.wait_for_function("window.__terrain3dLanding.phase === 'flying'")
        page.keyboard.up('Space')
        # A test pilot uses only public keyboard input; there is no autopilot in the app.
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            current = flight()
            if current['phase'] in ('landed', 'crashed'):
                break
            vertical_mps = current['vy'] / .14
            desired_mps = -min(4, max(.6, current['altitude'] * .6))
            if vertical_mps < desired_mps:
                page.keyboard.down('Space')
            else:
                page.keyboard.up('Space')
            page.wait_for_timeout(65)
        page.keyboard.up('Space')
        assert flight()['phase'] == 'landed', flight()
        assert dialog.get_by_text('Touchdown confirmed', exact=True).is_visible()
        page.screenshot(path=str(OUT/'voyager-touchdown.png'))
        dialog.get_by_role('button', name='Return to explorer', exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.body === 'Moon'")
        print('PASS safe manual touchdown through thrust modulation, live instruments and exit', flush=True)

        page.set_viewport_size({'width': 390, 'height': 844})
        dialog.get_by_role('button', name='Rover', exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.vehicle === 'rover'")
        page.screenshot(path=str(OUT/'rover-mobile.png'))
        dialog.get_by_role('button', name='Pilot Voyager', exact=True).click()
        page.wait_for_function("window.__terrain3dLanding?.phase === 'ready'")
        thrust = dialog.get_by_role('button', name='Fire thrusters', exact=True)
        thrust.hover(); page.mouse.down(); page.wait_for_function('window.__terrain3dLanding.thrust')
        page.wait_for_timeout(200); page.mouse.up()
        page.wait_for_function('window.__terrain3dLanding.thrust === false')
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        for label in ('Fire thrusters', 'Brake Voyager', 'Return to explorer', 'Restart Voyager landing'):
            button = dialog.get_by_role('button', name=label, exact=True)
            box = button.bounding_box()
            assert box and box['y'] >= 0 and box['y'] + box['height'] <= 844, label
        page.screenshot(path=str(OUT/'voyager-mobile.png'))
        dialog.get_by_role('button', name='Return to explorer', exact=True).click()
        page.keyboard.press('Escape')
        assert page.get_by_role('dialog').count() == 0
        assert page.get_by_role('button', name='Enter POV').first.evaluate('el => el === document.activeElement')
        assert not errors, errors
        print('PASS mobile hold controls, viewport layout, Escape and restored focus; no runtime errors', flush=True)
    finally:
        browser.close()
