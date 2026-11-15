"""Full rover controls, SI physics, source provenance and mobile layout checks."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.environ.get('TERRAIN_URL','http://127.0.0.1:5176')
OUT=Path(os.environ.get('ROVER_SCREENSHOTS','/tmp/astromatch-rover'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROME_PATH'),headless=True,args=['--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('console',lambda message:errors.append(message.text) if message.type=='error' and ('THREE.' in message.text or 'WebGL' in message.text) else None)
    try:
        page.goto(BASE+'/tests/rover.html',wait_until='networkidle')
        page.get_by_role('button',name='Enter POV').first.click()
        dialog=page.get_by_role('dialog',name='Planet terrain explorer')
        dialog.get_by_role('button',name='Rover',exact=True).click()
        page.wait_for_function("window.__terrain3dPov?.vehicle==='rover'&&window.__terrain3dPov.contacts===6")
        state=lambda:page.evaluate('window.__terrain3dPov')
        assert dialog.get_by_role('button',name='Hovercraft',exact=True).count()==0
        before=state()['player'];page.keyboard.down('w');page.wait_for_timeout(900);page.keyboard.up('w')
        assert state()['player']!=before
        assert abs(state()['speed'])>.1
        dialog.get_by_role('combobox',name='Rover drive profile').select_option('mer')
        page.wait_for_timeout(700)
        page.keyboard.down('w');page.wait_for_timeout(700);page.keyboard.up('w')
        assert abs(state()['speed'])<.08
        dialog.get_by_role('combobox',name='Rover drive profile').select_option('training')
        assert dialog.get_by_role('combobox',name='Simulation time scale').input_value()=='1'
        page.keyboard.down('w');page.wait_for_timeout(1500);page.keyboard.up('w')
        assert state()['speed']>.5,state()
        page.keyboard.down('Space');page.wait_for_timeout(1200);page.keyboard.up('Space')
        assert abs(state()['speed'])<.06
        page.keyboard.down('s');page.wait_for_timeout(1400)
        assert state()['speed']<-.3,state()
        page.keyboard.up('s');page.keyboard.down('w');page.wait_for_timeout(2500);page.keyboard.up('w')
        assert state()['speed']>.3,state()
        page.keyboard.down('a');page.wait_for_timeout(300)
        assert state()['wheels'][0]['steering']!=0
        assert state()['wheels'][0]['steering']*state()['wheels'][2]['steering']<0
        page.keyboard.down('w');page.wait_for_timeout(900);page.keyboard.up('w');page.keyboard.up('a')
        page.screenshot(path=str(OUT/'rover-mars.png'))
        print('PASS MER speed limit, training profile, throttle, brake, four-wheel steering and six contacts',flush=True)

        page.keyboard.press('p');page.wait_for_function('window.__terrain3dPov.paused')
        page.wait_for_timeout(200);stopped=state()['player'];page.wait_for_timeout(400);assert state()['player']==stopped
        reference=dialog.locator('details.rover-reference');reference.locator('summary').click()
        assert dialog.get_by_role('region',name='Rover instruments').is_visible()
        slider=dialog.get_by_role('slider',name='Archived RMC record')
        slider.evaluate("el=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'36');el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}")
        assert '2:50:0:6:0' in reference.inner_text()
        assert 'not registered' in reference.inner_text()
        assert state()['player']==stopped
        reference.locator('summary').click()
        dialog.get_by_role('button',name='Resume simulation',exact=True).click()
        page.wait_for_function('!window.__terrain3dPov.paused')
        dialog.get_by_role('button',name='Recover rover',exact=True).click()
        page.wait_for_function('window.__terrain3dPov.contacts===6')
        dialog.get_by_role('combobox',name='Explorer camera').select_option('first');page.wait_for_function("window.__terrain3dPov.view==='first'")
        dialog.get_by_role('combobox',name='Explorer camera').select_option('third')
        print('PASS pause/resume, original PDS coordinate study, no false terrain registration, recover and mast camera',flush=True)

        for body in ('Earth','Moon','Mars'):
            dialog.get_by_role('button',name=body,exact=True).click()
            page.wait_for_function("body=>window.__terrain3dPov?.body===body&&window.__terrain3dPov.contacts===6",arg=body)
            assert all(abs(v)<1000 for v in state()['player'])
        dialog.get_by_role('button',name='Recover rover',exact=True).click()
        dialog.get_by_role('combobox',name='Simulation time scale').select_option('5')
        page.keyboard.down('s');page.wait_for_timeout(4200);page.keyboard.up('s')
        assert state()['boundaryBlocked'],state()
        assert 0<=state()['location']['u']<=1 and 0<=state()['location']['v']<=1
        dialog.get_by_role('button',name='Recover rover',exact=True).click()
        dialog.get_by_role('combobox',name='Simulation time scale').select_option('1')
        print('PASS planet world recreation, selected-parcel geofence and recovery',flush=True)

        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500)
        forward=dialog.get_by_role('button',name='Move forward',exact=True)
        before=state()['player'];forward.hover();page.mouse.down();page.wait_for_timeout(500);page.mouse.up()
        assert state()['player']!=before
        brake=dialog.get_by_role('button',name='Brake rover',exact=True);brake.hover();page.mouse.down();page.wait_for_timeout(700);page.mouse.up()
        assert abs(state()['speed'])<.07
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        console=dialog.locator('.rover-console').bounding_box();pad=dialog.locator('.explorer-dpad').bounding_box()
        assert console['x']+console['width']<=pad['x']+1,(console,pad)
        page.screenshot(path=str(OUT/'rover-mobile.png'))
        page.keyboard.press('Escape');assert page.get_by_role('dialog').count()==0
        assert page.get_by_role('button',name='Enter POV').first.evaluate('el=>el===document.activeElement')
        assert not errors,errors
        print('PASS mobile drive and brake, instrument layout, focus restoration and no shader/runtime errors',flush=True)
    finally:browser.close()
