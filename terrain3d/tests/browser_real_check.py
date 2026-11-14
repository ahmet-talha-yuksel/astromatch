import os
from playwright.sync_api import sync_playwright

BASE=os.environ.get('TERRAIN_URL','http://localhost:5174')
CHROME=os.environ.get('CHROME_PATH','C:/Program Files/Google/Chrome/Application/chrome.exe')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=CHROME,headless=True,args=['--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1366,'height':768}); errors=[]; failed=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.on('requestfailed',lambda r: failed.append(r.url))
    page.goto(BASE,wait_until='domcontentloaded'); page.wait_for_timeout(1800)
    assert page.locator('canvas').count()==2
    assert page.get_by_text('REAL SOURCE-DERIVED',exact=True).count()==1
    assert page.get_by_text('Jezero',exact=True).count()>=1
    assert page.get_by_text('Lake Salda',exact=True).count()>=1
    assert page.get_by_text('Awaiting similarity engine data',exact=True).count()==1
    assert page.get_by_text('Awaiting similarity engine data',exact=True).count()==1
    for value, target in [('shackleton-kula','Shackleton'),('jezero-salda','Jezero')]:
        page.locator('select').first.select_option(value); page.wait_for_timeout(1200)
        assert page.locator('canvas').count()==2
        assert page.get_by_text(target,exact=False).count()>=1
        assert page.get_by_text('REAL SOURCE-DERIVED',exact=True).count()==1
        if value == 'shackleton-kula':
            assert page.get_by_text('DIAGNOSTIC / UNCALIBRATED', exact=False).count()==1
            assert page.get_by_text('#3', exact=False).count()>=1
            assert page.get_by_text('2.07', exact=False).count()>=1
            assert page.get_by_text('displayed Terrain3D 20×20', exact=False).count()==1
        else:
            assert page.get_by_text('Awaiting similarity engine data', exact=True).count()==1
    # Controls and synchronized camera state on a real pair.
    page.get_by_role('checkbox',name='Sync Cameras').check(); canvases=page.locator('canvas')
    before=page.evaluate('window.__terrain3dCameraStates')
    box=canvases.nth(0).bounding_box(); x=box['x']+box['width']/2; y=box['y']+box['height']/2
    page.mouse.move(x,y); page.mouse.down(button='left'); page.mouse.move(x+80,y+20,steps=8); page.mouse.up(button='left'); page.wait_for_timeout(300)
    after=page.evaluate('window.__terrain3dCameraStates'); assert before != after
    page.locator('select').nth(1).select_option('relative'); page.locator('input[aria-label="Shared exaggeration"]').fill('2.0')
    assert page.get_by_text('Relative mode is display-only',exact=False).count()==1
    # Responsive layouts retain both canvases and the real label.
    page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(500); assert page.locator('canvas').count()==2
    page.screenshot(path='qa-screens/terrain3d-real-390x844.png',full_page=True)
    page.set_viewport_size({'width':1920,'height':1080}); page.wait_for_timeout(500); page.screenshot(path='qa-screens/terrain3d-real-1920x1080.png',full_page=True)
    page.set_viewport_size({'width':1366,'height':768}); page.screenshot(path='qa-screens/terrain3d-real-1366x768.png',full_page=True)
    assert not failed, failed; assert not errors, errors
    print('PASS real DEM pairs, selector, canvases, sync, relative mode, exaggeration, responsive screenshots')
    browser.close()
