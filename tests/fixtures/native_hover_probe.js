// Synthetic native-host probe only. Observe real projections; never inject exits.
window.runNativeHoverProbe = async () => {
  const checks=[], stages=[];
  const original=window.monitorPointer;
  let sequence=0, lastOutside=null, lastPoint='unobserved';
  window.monitorPointer=function(...args) {
    const result=original.apply(this,args);
    sequence++;
    lastPoint=args[0]===null?'outside':'inside';
    if(args[0]===null && args[1]!==false)lastOutside={sequence,time:performance.now()};
    return result;
  };
  async function waitForExit(stage,closed,deliveryDeadline=5000) {
    const start=performance.now(), baseline=sequence;
    let firstOutside=null,expired=false;
    let deadline=setTimeout(()=>{expired=true;},deliveryDeadline);
    try {
      while(true) {
        const now=performance.now();
        if(firstOutside===null && lastOutside?.sequence>baseline) {
          firstOutside=lastOutside.time;
          clearTimeout(deadline);
          deadline=setTimeout(()=>{expired=true;},1000);
        }
        const ok=firstOutside!==null && closed();
        // Use scheduled deadlines, not elapsed-time comparisons: after a busy
        // WebKit frame, an overdue polling microtask can precede the close timer.
        // The native host also imposes its independent wall-clock deadline.
        const reason=firstOutside===null ? 'outside sample not delivered' : 'automatic close not observed';
        if(ok || expired) {
          stages.push({stage,ok,elapsedMs:Math.round(now-start),
            firstOutsideMs:firstOutside===null?null:Math.round(firstOutside-start),
            outsideDelivered:firstOutside!==null,lastPoint,reason:ok?'closed':reason});
          return ok;
        }
        await new Promise(resolve=>setTimeout(resolve,20));
      }
    } finally {clearTimeout(deadline);}
  }
  try {
    // Font load does not mean queued startup pointer evaluations have drained.
    // Establish actual outside delivery before opening anything to measure.
    if(!await waitForExit('readiness',()=>true,5000))return {done:true,checks:[false],stages};
    document.querySelector('#agents .avatar').click();
    checks.push(!document.querySelector('#peek').hidden,
      document.querySelectorAll('#compact [title]').length===0);
    checks.push(await waitForExit('agent',()=>document.querySelector('#peek').hidden));
    document.querySelector('#quota').click();
    checks.push(!document.querySelector('#peek').hidden);
    checks.push(await waitForExit('quota',()=>document.querySelector('#peek').hidden));
    document.querySelector('#expand').click();
    checks.push(!document.querySelector('#expanded').hidden,
      document.querySelectorAll('header,#collapse,#hide').length===0);
    checks.push(await waitForExit('island',()=>!document.querySelector('#compact').hidden));
    return {done:true,checks,stages};
  } finally {
    window.monitorPointer=original;
  }
};
