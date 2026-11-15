"""Capture the README images from a running app using its public UI controls.

pip install playwright
CHROME_PATH=/path/to/chrome ASTROMATCH_UI_URL=http://localhost:5173 python docs/capture_screenshots.py
No API responses, scores, labels or page styles are replaced for these images.
"""
import os
from pathlib import Path
import re

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/images'
BASE = os.environ.get('ASTROMATCH_UI_URL', 'http://localhost:5173')


def capture(page, name):
    page.mouse.move(1590, 1090)
    page.screenshot(path=str(OUTPUT/name), type='jpeg', quality=90, animations='disabled')
    print('Captured', name, flush=True)


def comparison_ready(page):
    page.wait_for_function("document.querySelectorAll('.terrain-embed canvas').length === 2", timeout=60000)
    page.locator('.candidate-item').first.wait_for(timeout=30000)
    page.locator('.main-area').evaluate('(el) => el.scrollTo(0,0)')
    page.wait_for_timeout(1200)


with sync_playwright() as p:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    options = {'headless': True, 'args': ['--enable-unsafe-swiftshader']}
    if os.environ.get('CHROME_PATH'):
        options['executable_path'] = os.environ['CHROME_PATH']
    browser = p.chromium.launch(**options)
    try:
        page = browser.new_page(viewport={'width':1600,'height':1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console',lambda message: errors.append(message.text)
            if message.type=='error' and ('THREE.' in message.text or 'WebGL' in message.text) else None)
        page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
        comparison_ready(page)
        page.get_by_role('button',name='Pause space animation',exact=True).click()
        if page.locator('.app-shell').get_attribute('data-body') != 'mars':
            page.get_by_role('button',name='Switch to Mars',exact=True).click()
            page.wait_for_function("document.querySelector('.app-shell').dataset.body === 'mars'")
            comparison_ready(page)
        page.get_by_role('combobox',name='TARGET REGION',exact=True).click()
        page.get_by_role('option',name=re.compile(r'^T-01\b')).click()
        comparison_ready(page)
        capture(page,'terrain-comparison.jpg')

        profile=page.get_by_role('region',name='Analog profile',exact=True)
        profile.locator('.profile-dimension').first.wait_for(timeout=30000)
        profile.screenshot(path=str(OUTPUT/'analog-profile.jpg'),type='jpeg',quality=90,animations='disabled')
        print('Captured analog-profile.jpg',flush=True)

        page.get_by_role('button',name='Explore surface',exact=True).click()
        dialog=page.get_by_role('dialog',name='Planet terrain explorer')
        dialog.get_by_role('button',name='Rover',exact=True).click()
        page.wait_for_function("(() => { const el=document.querySelector('.rover-console-heading strong'); return el && !el.textContent.includes('INITIALIZING'); })()",timeout=30000)
        page.wait_for_timeout(2500)
        assert 'UNAVAILABLE' not in page.locator('.rover-console-heading strong').inner_text()
        canvas=dialog.locator('canvas');box=canvas.bounding_box()
        page.mouse.move(box['x']+1000,box['y']+400);page.mouse.down()
        page.mouse.move(box['x']+800,box['y']+440,steps=15);page.mouse.up()
        page.wait_for_timeout(700)
        capture(page,'rover-explorer.jpg')
        page.keyboard.press('Escape')

        page.get_by_role('button',name='Switch to Moon',exact=True).click()
        page.wait_for_function("document.querySelector('.app-shell').dataset.body === 'moon'")
        page.get_by_role('combobox',name='TARGET REGION',exact=True).click()
        page.get_by_role('option',name=re.compile(r'^T-02\b')).click()
        comparison_ready(page)
        capture(page,'moon-earth-comparison.jpg')

        page.get_by_role('button',name='Explore surface',exact=True).click()
        dialog=page.get_by_role('dialog',name='Planet terrain explorer')
        dialog.get_by_role('button',name='Pilot Voyager',exact=True).click()
        dialog.get_by_text('Ready for your command',exact=True).wait_for(timeout=15000)
        page.wait_for_timeout(1000)
        capture(page,'voyager-landing.jpg')
        page.keyboard.press('Escape')
        assert not errors, errors
        print('PASS: five screenshots captured from the live app; no runtime or shader errors.',flush=True)
    finally:
        browser.close()
