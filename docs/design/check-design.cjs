// Local prototype QA. No account, installed app, or live router is accessed.
const {chromium}=require('playwright');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1040},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(__dirname,'monitor-directions.html')).href);
  const out=path.resolve(__dirname,'../../state/design');fs.mkdirSync(out,{recursive:true});
  for(const mode of ['capsule','tray','sidebar']){
    await page.locator('#tab-'+mode).click();
    await page.screenshot({path:path.join(out,mode+'.png'),fullPage:true});
    await page.locator('#why').click();
    if(!await page.locator('#reason').isVisible())throw Error('Reason hidden');
    const contained=await page.evaluate(()=>{const a=document.getElementById('stage').getBoundingClientRect(),b=document.getElementById('surface').getBoundingClientRect();return b.top>=a.top&&b.bottom<=a.bottom});
    if(!contained)throw Error('Expanded panel clips outside stage: '+mode);
    await page.locator('#why').click();
    await page.locator('#toggle').click();
    if(await page.locator('#surface').isVisible())throw Error('Panel did not collapse');
    await page.locator('#toggle').click();
  }
  await page.locator('#pause').click();
  if(await page.locator('#pause').getAttribute('aria-pressed')!=='true')throw Error('Pause state');
  await page.locator('#pin').click();
  if(await page.locator('#pin').getAttribute('aria-pressed')!=='true')throw Error('Pin state');
  await page.keyboard.press('Escape');
  if(await page.locator('#surface').isVisible())throw Error('Escape');
  await page.setViewportSize({width:390,height:1000});
  await page.locator('#tab-capsule').click();
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  await page.locator('#why').click();
  const mobileContained=await page.evaluate(()=>{const a=document.getElementById('stage').getBoundingClientRect(),b=document.getElementById('surface').getBoundingClientRect();return b.top>=a.top&&b.bottom<=a.bottom});
  if(!mobileContained)throw Error('Mobile expanded panel clipped');
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  if(overflow||errors.length)throw Error(JSON.stringify({overflow,errors}));
  console.log('Three designs, expand/collapse, reasoning, pause, pin, Escape and 390px layout: OK');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
