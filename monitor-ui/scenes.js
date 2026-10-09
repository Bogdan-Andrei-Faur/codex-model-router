/* Original rigid companion props. Status symbols use the bundled Lucide library. */
globalThis.RouterScenes = {
  draw(svg, icon, kind) {
    const root=svg('g',{class:'activity-prop','data-kind':kind,'aria-hidden':'true'});
    const group=(cls,parent=root)=>{const n=svg('g',{class:cls});parent.append(n);return n;};
    const put=(tag,attrs,parent=root)=>{const n=svg(tag,attrs);parent.append(n);return n;};
    const rect=(x,y,width,height,fill,rx=3,parent=root)=>put('rect',{x,y,width,height,rx,fill},parent);
    const line=(d,stroke='#748599',width=2,parent=root)=>put('path',{d,fill:'none',stroke,'stroke-width':width,'stroke-linecap':'round','stroke-linejoin':'round'},parent);
    const dot=(cx,cy,r,fill,parent=root)=>put('circle',{cx,cy,r,fill},parent);
    const glyph=(name,x,y,size,color,parent=root)=>{const n=icon(name);for(const [k,v] of Object.entries({x,y,width:size,height:size,color,class:'scene-symbol','stroke-width':2.4}))n.setAttribute(k,v);parent.append(n);return n;};
    const paper=(x,y,w,h,parent=root)=>{rect(x+1,y+2,w,h,'#29313d',3,parent);rect(x,y,w,h,'#f3ede1',3,parent);};
    const badge=(name,color,cls='status-symbol')=>{const g=group(cls);rect(78,-12,26,26,'#18212d',8,g);rect(79,-11,24,24,'#263341',7,g);glyph(name,82,-8,18,color,g);return g;};
    const keyboard=(parent=root)=>{
      rect(15,76,70,19,'#344454',4,parent);rect(17,75,66,17,'#b8c6d3',3,parent);
      for(let row=0;row<2;row++)for(let col=0;col<9;col++)rect(21+col*6.6,78+row*4.5,4.6,2.8,'#526577',.7,parent);
      rect(35,87,30,2.8,'#526577',.7,parent);
    };
    const laptop=(mode,parent=root)=>{
      const g=group('laptop',parent);
      rect(17,66,66,27,'#354557',4,g);rect(20,68,60,21,'#101e2b',2,g);
      if(mode==='terminal'){
        line('M25 73L29 76L25 79','#83dcc0',1.8,g);line('M34 77H49 M25 84H58','#b8d8ed',1.8,g);
        rect(53,74,4,5,'#f3cc77',.5,group('terminal-cursor',g));
      }else{
        rect(23,71,54,4,'#607488',1,g);
        for(let i=0;i<3;i++)rect(24,79+i*4,32-i*5,1.5,'#91bdd6',.5,g);
        dot(68,82,5,'#5c91b0',g);
      }
      put('path',{d:'M17 91H83L90 98H10Z',fill:'#a8b9c8',stroke:'#354557','stroke-width':1.5},g);
      for(let i=0;i<9;i++)line(`M${21+i*6.5} 93v2`,'#526577',1,g);
      line('M40 96H60','#6a7e90',1.3,g);return g;
    };
    if(kind==='thinking'){
      const g=group('thought-cloud');
      dot(69,14,2.8,'#f2f6fa',g);dot(75,6,4,'#f2f6fa',g);
      put('path',{d:'M67 -3C59 -3 59 -15 67 -16C69 -24 83 -24 87 -17C99 -19 106 -6 97 0H72Z',fill:'#f2f6fa',stroke:'#cbd7e4','stroke-width':1},g);
    }else if(kind==='writing'){
      keyboard();
    }else if(kind==='executing'||kind==='working'){
      laptop(kind==='executing'?'terminal':'work');
      if(kind==='working')dot(68,82,2,'#f5dc9b',group('work-indicator'));
    }else if(kind==='searching'){
      // Back-facing body sits in front of the laptop: the visible screen is above its shoulders.
      const g=group('search-laptop');rect(9,-21,82,49,'#a8bacb',5,g);rect(13,-17,74,39,'#1a2e40',3,g);
      rect(17,-13,66,7,'#e8eef2',2,g);glyph('search',19,-12,5,'#506b80',g);
      line('M29 -9H67','#8ba4b7',1.3,g);
      for(let i=0;i<3;i++){rect(19,-1+i*7,10,4,'#6995b2',1,g);line(`M34 ${i*7+1}H76`,'#c2d5e0',2,g);}
      rect(18,-2,61,7,'#9bdcc5',1,group('search-highlight',g));
      put('path',{d:'M9 25H91L98 32H2Z',fill:'#c4d0d9'},g);
    }else if(kind==='editing'||kind==='planning'||kind==='reviewing'){
      paper(26,68,50,29);
      line('M33 74H67 M33 81H67 M33 88H60','#b0babf',1.4);
      if(kind==='planning'){
        rect(42,65,18,6,'#b39bd9',2);
        for(let i=0;i<3;i++)rect(30,72+i*7,3,3,'#dbbf78',.6);
        const g=group('plan-marker');line('M34 74H57','#597798',2.5,g);
      }else if(kind==='reviewing'){
        const g=group('review-scan');line('M33 75H67','#518d9d',2,g);
        glyph('check',62,81,10,'#318575');
      }else{
        line('M51 70V95','#d0c9b9',1);line('M31 86H45','#568597',1.5);
        const g=group('pencil');put('path',{d:'M55 89L70 61L76 64L61 92L54 96Z',fill:'#e6b96f',stroke:'#6b563e','stroke-width':1},g);
        line('M58 89L73 64','#f7dc9e',1.4,g);put('path',{d:'M54 96L55 90L61 92Z',fill:'#374151'},g);line('M70 61L76 64','#d8848f',4,g);
      }
    }else if(kind==='generating'){
      line('M64 45L58 98 M82 45L91 98 M59 89H91','#bd9367',3);
      paper(58,42,38,44);rect(61,45,32,37,'#edf4ee',1);
      dot(84,54,4,'#ebc36a');
      const g=group('paint-reveal');put('path',{d:'M63 78L74 60L90 78Z',fill:'#8fbac9'},g);put('path',{d:'M62 78L71 69L80 78Z',fill:'#80baa1'},g);
      const brush=group('paint-brush');line('M49 86L73 66','#d5a373',4,brush);line('M70 69L76 64','#adc4cf',4,brush);put('path',{d:'M74 66Q73 58 81 59Q81 66 76 67Z',fill:'#7dabca'},brush);
    }else if(kind==='inspecting'){
      const g=group('magnifier');dot(70,53,14,'#d3effa',g);dot(70,53,11,'#34566b',g);dot(70,53,8.5,'#bdddea',g);
      line('M65 49Q70 45 74 49','#f5fbff',2,g);line('M81 65L92 79','#cedbe4',6,g);line('M85 70L92 79','#b5956d',5,g);
    }else if(kind==='tool'){
      const g=group('spanner');glyph('wrench',56,53,39,'#d3dfe9',g);
      const driver=group('screwdriver');line('M29 79L18 54','#bbcbd8',3,driver);put('path',{d:'M17 54L15 46L19 45L21 53Z',fill:'#cbd7df'},driver);line('M29 78L34 89','#d6a55d',7,driver);line('M29 80L32 87','#f4d592',1.2,driver);
    }else if(kind==='collaborating'){
      // Two independent notes meet on a common board: a concrete exchange, not a greeting.
      const partner=group('collaboration-partner');rect(81,46,25,24,'#b8a5d6',8,partner);dot(89,55,1.7,'#333443',partner);dot(99,55,1.7,'#333443',partner);line('M90 62Q94 65 98 62','#333443',1.3,partner);rect(85,67,5,5,'#a08cbc',2,partner);rect(98,67,5,5,'#a08cbc',2,partner);
      rect(22,72,56,24,'#33485b',4);line('M50 76V91','#71899e',1);
      const a=group('shared-note-left');paper(23,66,21,17,a);line('M27 72H39 M27 77H36','#538c87',1.7,a);
      const b=group('shared-note-right');paper(56,66,21,17,b);line('M60 72H72 M60 77H69','#8a78b5',1.7,b);
      line('M44 87H56 M53 84L56 87L53 90','#a5d8dc',1.8);
    }else if(kind==='compacting'){
      const pile=group('sorted-stack');paper(57,85,27,9,pile);paper(57,80,27,9,pile);paper(57,75,27,9,pile);
      for(let i=0;i<3;i++){
        const sheet=group('sort-sheet sheet-'+i);paper(17,65+i*8,27,9,sheet);line(`M22 ${69+i*8}H36`,'#789aaa',1.3,sheet);
      }
    }else if(kind==='preparing'){
      rect(19,77,62,18,'#38516a',4);rect(22,81,56,10,'#536f85',2);
      const g=group('prepare-folder');paper(23,64,30,17,g);rect(25,61,13,5,'#d7b577',2,g);line('M28 70H47','#a3adab',1.4,g);
      const pencil=group('prepare-pencil');line('M67 86V59','#dbb574',4,pencil);put('path',{d:'M65 59L67 53L69 59Z',fill:'#e8ddc8'},pencil);
    }else if(kind==='waiting'){
      // Rounded forearms meet across the lower face; original side hands remain attached.
      const g=group('folded-arms limbs');line('M17 66Q27 80 59 74','var(--character)',8,g);line('M83 66Q69 81 42 74','var(--character)',8,g);line('M42 78Q50 79 58 77','#283e3c',1.2,g);
    }else if(kind==='offline'){
      const z=group('sleep-marks');line('M74 8H81L74 15H81 M86 -4H95L86 5H95','#a6b9db',2,z);
    }else if(kind==='unknown'){
      const g=group('unknown-dashes');line('M80 5H85 M80 11H89','#afbdcc',2,g);
    }else if(kind==='retrying'){
      const g=badge('rotate-cw','#f1cc76','retry-symbol');
      const symbol=g.querySelector('.scene-symbol'),spin=svg('g',{class:'retry-arrow'});spin.append(...symbol.childNodes);symbol.append(spin);
    }else if(kind==='error'){
      badge('triangle-alert','#ff8a92');line('M31 41L41 44 M59 44L69 41','#4a2d38',2);
    }else if(kind==='done'){
      badge('check','#9aecd1');
    }else if(kind==='approval'){
      badge('lock-keyhole','#f0cb80');
    }else if(kind==='question'){
      badge('circle-help','#a8d8ff');
    }else if(kind==='interrupted'){
      line('M42 64H57','#39515c',2.5);line('M58 64V73','#9ec5d7',2.3);
    }
    return root;
  }
};
