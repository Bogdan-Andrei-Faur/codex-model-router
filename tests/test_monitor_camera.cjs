// Camera exclusion and display changes use synthetic data, never owner state.
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    for(const scale of [1,2]) {
      const page=await browser.newPage({viewport:{width:800,height:1000},deviceScaleFactor:scale});
      const errors=[];page.on('pageerror',e=>errors.push(String(e)));
      await page.goto(pathToFileURL(path.resolve(__dirname,'../monitor-ui/index.html')).href);
      const widths=[];
      for(const count of [0,1,2,3,5,9,40,1]) {
        await page.evaluate(count=>window.receive({connections:1,threads:Object.fromEntries(Array.from({length:count},(_,i)=>['agent'+i,{name:'Synthetic agent '+i,status:'active',model:'gpt-6.1-sol'}])),ui:{mode:'Compact',reduced:true,cameraWidth:185,cameraHeight:32}}),count);
        await page.waitForTimeout(500);
        const bounds=await page.locator('#surface').boundingBox();
        widths.push(bounds.width);
        assert.equal(bounds.y,0);assert.ok(bounds.x>=0 && bounds.x+bounds.width<=800);
        for(const button of await page.locator('.capsule-bar button:visible').all()) {
          const r=await button.boundingBox();
          assert.ok(r.x+r.width<=307.5 || r.x>=492.5 || r.y>=32,'Control intersects camera');
        }
        assert.equal(await page.locator('.camera-gap').evaluate(n=>n.getBoundingClientRect().x+n.getBoundingClientRect().width/2),400);
      }
      assert.ok(widths[1]<=440,'One agent should stay compact');
      assert.ok(widths[2]>=widths[1] && widths[3]>widths[2] && widths[4]>widths[3],'Width grows with agents');
      assert.ok(widths[5]<=631 && widths[6]===widths[5],'Overflow must cap the width');
      assert.equal(widths[7],widths[1],'Width contracts after agents finish');
      await page.locator('#expand').click();
      await page.waitForTimeout(500);
      assert.ok((await page.locator('nav').boundingBox()).y<10,'Expanded navigation must use upper wings');
      for(const tab of ['home','activity','history','statistics','settings']) {
        await page.locator('nav [data-tab="'+tab+'"]').click();
        await page.waitForTimeout(500);
        for(const button of await page.locator('nav button').all()) {
          const r=await button.boundingBox();
          assert.ok(r.y<16 && (r.x+r.width<=307.5 || r.x>=492.5),'Navigation intersects camera');
        }
      }
      // Compact-window animation may clip controls but never reveal them over the camera.
      await page.evaluate(()=>document.querySelector('#surface').style.width='440px');
      for(const x of [308,350,400,450,492])assert.equal(await page.evaluate(x=>!!document.elementFromPoint(x,20)?.closest('button'),x),false);
      await page.evaluate(()=>document.querySelector('#surface').style.removeProperty('width'));

      await page.evaluate(()=>window.receiveUI({mode:'Compact',cameraWidth:0,cameraHeight:0}));
      await page.waitForTimeout(500);
      assert.equal(await page.locator('body').evaluate(n=>n.classList.contains('camera-wings')),false);
      assert.equal((await page.locator('#surface').boundingBox()).y,0);
      assert.equal((await page.locator('#surface').boundingBox()).height,64);
      assert.ok((await page.locator('#surface').boundingBox()).width<=430);
      // Narrow/unknown cutout geometry uses a safe vertical inset instead.
      await page.setViewportSize({width:390,height:900});
      await page.evaluate(()=>window.receiveUI({cameraWidth:185,cameraHeight:32}));
      await page.waitForTimeout(500);
      assert.ok((await page.locator('.capsule-bar').boundingBox()).y>=40);
      await page.evaluate(()=>window.receiveUI({mode:'Expanded'}));
      await page.waitForTimeout(500);
      assert.ok((await page.locator('nav').boundingBox()).y>=40,'Narrow layout keeps safe vertical fallback');
      assert.deepEqual(errors,[]);
      await page.close();
    }
    console.log('PASS: camera exclusion, expanded safe inset, flat display, narrow fallback and 1x/2x');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
