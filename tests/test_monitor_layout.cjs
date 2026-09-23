// Local WebKit-surface layout checks in Chromium; native macOS still needs a Mac.
const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(String(error)));
    await page.addInitScript(()=>{
      window.nativeMessages=[];
      window.webkit={messageHandlers:{monitor:{postMessage:message=>window.nativeMessages.push(message)}}};
    });
    await page.route('**/codex.png',route=>route.fulfill({path:path.resolve(__dirname,'../assets/codex-official.png')}));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
    for (const height of [1020,1380,674,460]) {
      await page.setViewportSize({width:432,height});
      const preferred=Math.min(height,Math.max(560,(height+20)*.9));
      await page.evaluate(value=>window.receive({ui:{mode:'Expanded',topmost:true,reduced:true,panelHeight:value}}),preferred);
      const rect=await page.locator('#surface').boundingBox();
      assert.ok(Math.abs(rect.y+rect.height-(height-8))<1,'Bottom anchor moved');
      assert.ok(rect.y>=8 && rect.height<=height-16,'Panel exceeds available area');
      assert.ok(Math.abs(rect.height-(preferred-16))<1,'Adaptive height differs');
      const header=await page.locator('header').boundingBox(),footer=await page.locator('footer').boundingBox();
      assert.ok(header.y>=rect.y && footer.y+footer.height<=rect.y+rect.height,'Chrome escaped panel');
    }
    await page.setViewportSize({width:432,height:1020});
    await page.evaluate(()=>window.receive({ui:{mode:'Expanded',reduced:true,panelHeight:936}}));
    const before=await page.locator('#surface').boundingBox();
    const grip=await page.locator('#height-grip').boundingBox();
    await page.mouse.move(grip.x+grip.width/2,grip.y+7);
    await page.mouse.down();await page.mouse.move(grip.x+grip.width/2,grip.y+157,{steps:6});await page.mouse.up();
    const after=await page.locator('#surface').boundingBox();
    assert.ok(Math.abs(after.height-(before.height-150))<2,'Grip did not resize panel');
    assert.ok(Math.abs(after.y+after.height-before.y-before.height)<1,'Resize moved bottom');
    const message=await page.evaluate(()=>window.nativeMessages.filter(m=>m.action==='resizeEnd').at(-1));
    assert.ok(message && Math.abs(message.height-after.height-16)<1,'Native preference not submitted');
    await page.locator('#height-grip').focus();await page.keyboard.press('Home');
    assert.ok(await page.evaluate(()=>window.nativeMessages.some(m=>m.action==='resizeReset')),'Automatic height reset unavailable');
    assert.deepEqual(errors,[]);
    console.log('PASS: responsive height, fixed chrome, bottom anchor, drag persistence message and keyboard reset');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
