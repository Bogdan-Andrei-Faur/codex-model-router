/* Development-only loopback adapter. The packaged monitor never loads this. */
(()=>{
  const prefix=new URL('.',location.href),ui={mode:'Expanded',topmost:true,reduced:false,lazyHistory:true,acknowledgesMode:true,panelHeight:Math.min(innerHeight,780)};
  let needsHistory=false,revision=-1,busy=false,timer;
  async function poll(){
    if(busy)return;busy=true;
    try{
      const url=new URL('snapshot',prefix);url.searchParams.set('history',needsHistory?'1':'0');url.searchParams.set('revision',String(revision));
      const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error('preview unavailable');
      const payload=await response.json();
      if(payload.history)revision=payload.journalRevision;
      window.receive({...payload,ui:{...ui}});
    }catch{window.receive?.({connections:0});window.monitorFeedback?.('Vista previa desconectada.');}
    finally{busy=false;}
  }
  window.webkit={messageHandlers:{monitor:{postMessage(message){
    if(message.action==='mode'){ui.mode=message.value;ui.modeRequest=message.request;window.receiveUI({...ui},message.request);}
    else if(message.action==='history'){needsHistory=message.value;setTimeout(poll,0);}
    else if(message.action==='resizeEnd'){ui.panelHeight=message.height;}
    else if(message.action==='resizeReset'){ui.panelHeight=Math.min(innerHeight,780);window.receiveUI({...ui});}
    else if(message.action==='ready'){clearInterval(timer);setTimeout(poll,0);timer=setInterval(poll,2000);}
    else if(!['bounds','resizeStart'].includes(message.action))window.monitorFeedback?.('Vista previa de solo lectura.');
  }}}};
  document.addEventListener('DOMContentLoaded',()=>{setTimeout(poll,0);if(!timer)timer=setInterval(poll,2000);});
  window.addEventListener('pagehide',()=>clearInterval(timer));
})();
