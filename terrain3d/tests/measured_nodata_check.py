"""Verify NoData diagnostics against the running measured-data app/API.

Requires the app on 5173, API on 8000, and Playwright/Chrome. Reads data only.
"""
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('APP_URL', 'http://localhost:5173')
API = os.environ.get('API_URL', 'http://localhost:8000')
CHROME = os.environ.get('CHROME_PATH', 'C:/Program Files/Google/Chrome/Application/chrome.exe')
OUT = Path(__file__).resolve().parents[1] / 'qa-screens'
CASES = [('T-01', 'mars_jezero_regional'), ('T-04', 'mars_phoenix_regional'), ('T-05', 'mars_arcadia_regional')]

def data(region):
    with urlopen(f'{API}/api/v1/terrain/{region}', timeout=20) as response:
        return json.load(response)['viewer']

def digest(terrain):
    return hashlib.sha256(json.dumps(terrain, sort_keys=True).encode()).hexdigest()

OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1680, 'height': 1100})
    page.set_default_timeout(15000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and ('THREE.' in message.text or 'WebGL' in message.text) else None)
    try:
        page.goto(BASE, wait_until='domcontentloaded')
        page.get_by_role('combobox', name='TARGET REGION').wait_for()
        switch = page.get_by_role('button', name='Switch to Mars')
        if switch.count(): switch.click()
        expect(page.locator('.app-shell')).to_have_attribute('data-body', 'mars')
        for alias, region in CASES:
            original = data(region)
            missing = sum(value is None for value in original['heights'])
            percentage = 100 * missing / len(original['heights'])
            page.get_by_role('combobox', name='TARGET REGION').click()
            page.get_by_role('option').filter(has_text=re.compile(r'^' + alias + r'\s')).click()
            target = page.locator('.terrain-panel').first
            legend = target.get_by_role('note', name='Missing elevation data')
            expect(legend).to_contain_text(f'{percentage:.2f}%', timeout=15000)
            expect(target.locator('canvas')).to_have_count(1)
            expect(legend).to_have_attribute('data-fill-mode', 'estimated')
            toggle = target.get_by_role('button', name='Fill missing terrain (visual only)', exact=True)
            expect(toggle).to_have_attribute('aria-pressed', 'true')
            page.wait_for_timeout(700)
            target.screenshot(path=str(OUT / f'filled-{alias.lower()}.png'))
            toggle.click()
            expect(legend).to_have_attribute('data-fill-mode', 'gaps')
            expect(legend).to_contain_text('Hatched areas are unmeasured')
            page.wait_for_timeout(200)
            target.screenshot(path=str(OUT / f'nodata-{alias.lower()}.png'))
            toggle.click()
            expect(legend).to_have_attribute('data-fill-mode', 'estimated')
            if alias == 'T-04':
                page.get_by_role('button', name='Explore surface', exact=True).click()
                dialog = page.get_by_role('dialog', name='Planet terrain explorer')
                expect(dialog.get_by_role('note')).to_contain_text('Estimated fill: 7.92%')
                pov_toggle = dialog.get_by_role('button', name='Fill missing terrain (visual only)', exact=True)
                pov_toggle.click()
                expect(dialog.get_by_role('note')).to_contain_text('No elevation data: 7.92%')
                pov_toggle.click()
                expect(dialog.get_by_role('note')).to_contain_text('Estimated fill: 7.92%')
                page.wait_for_timeout(400)
                page.keyboard.press('Escape')
                expect(dialog).to_have_count(0)
            assert digest(original) == digest(data(region)), 'Rendering must not change measured heights or provenance'
            print(f'PASS {alias}: {missing}/{len(original["heights"])} missing samples ({percentage:.2f}%), estimated fill/gap toggle, unchanged source', flush=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        legend = page.locator('.terrain-panel').first.get_by_role('note', name='Missing elevation data')
        legend.scroll_into_view_if_needed()
        expect(legend).to_be_visible()
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        assert not errors, errors
        print('PASS mobile legend, POV explanation, no shader/runtime errors', flush=True)
    finally:
        browser.close()
