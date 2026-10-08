/* Original companion wardrobe artwork. UI controls continue to use Lucide. */
globalThis.RouterCharacters = {
  draw(svg, look, clipId) {
    const group=svg('g',{class:'character-accessories'}),cloth=svg('g',{'clip-path':'url(#'+clipId+')','data-slot':'outfit'});
    const ink='#29282c', light='#fff4e2', color='var(--accessory)';
    const path=(d,fill=color,extra={})=>svg('path',{d,fill,...extra});
    const line=(d,stroke=light,width=2)=>path(d,'none',{stroke,'stroke-width':width,'stroke-linecap':'round','stroke-linejoin':'round'});
    const rect=(x,y,width,height,rx=2,fill=color)=>svg('rect',{x,y,width,height,rx,fill});
    const dot=(cx,cy,r,fill=light)=>svg('circle',{cx,cy,r,fill});
    // Lower-body garments follow the same rounded silhouette; the mouth stays free.
    if(look.outfit!=='none') {
      if(look.outfit==='tee')cloth.append(path('M11 64 L30 68 L37 72 L63 72 L70 68 L89 64 V85 H11 Z'),line('M38 72 Q50 79 62 72'));
      if(look.outfit==='sweater')cloth.append(rect(11,69,78,16,0),line('M35 70 Q50 78 65 70'),line('M22 81 H78'),line('M24 78 V84 M31 78 V84 M69 78 V84 M76 78 V84',light,1.4));
      if(look.outfit==='hoodie')cloth.append(path('M12 66 Q23 57 33 66 L40 72 H60 L67 66 Q77 57 88 66 V86 H12 Z'),line('M29 64 Q34 72 40 73 M71 64 Q66 72 60 73'),line('M39 73 V79 M61 73 V79'),line('M43 82 Q50 78 57 82',ink,1.8));
      if(look.outfit==='overalls')cloth.append(rect(30,68,40,18,4),rect(29,60,7,20,2),rect(64,60,7,20,2),dot(33,73,1.8),dot(67,73,1.8),line('M42 77 H58 V83 H42 Z',light,1.5));
      if(look.outfit==='vest')cloth.append(path('M16 63 L32 66 L45 76 L45 85 H11 Z M84 63 L68 66 L55 76 V85 H89 Z'),line('M32 67 L43 76 V84 M68 67 L57 76 V84'),dot(51,79,1.5,ink));
      if(look.outfit==='jacket')cloth.append(path('M12 63 L29 64 L43 73 H57 L71 64 L88 63 V86 H12 Z'),line('M31 65 L38 75 L44 72 M69 65 L62 75 L56 72'),line('M50 74 V85',ink),line('M22 78 H32 M68 78 H78',light,1.7));
      if(look.outfit==='labcoat')cloth.append(path('M12 64 L28 63 L42 72 H58 L72 63 L88 64 V86 H12 Z',light),line('M29 65 L37 77 L44 72 M71 65 L63 77 L56 72',color),line('M50 75 V85',color,1.5),rect(66,76,10,7,1,color),dot(53,79,1.2,color));
      group.append(cloth);
    }
    const detail=svg('g',{'data-slot':'detail','clip-path':'url(#'+clipId+')'});
    if(look.detail==='pocket')detail.append(path('M61 74 H75 V81 Q68 88 61 81 Z',light),line('M63 76 H73',color,1.5));
    if(look.detail==='buttons')detail.append(dot(50,74,1.8,ink),dot(50,79,1.8,ink),dot(50,84,1.8,ink));
    if(look.detail==='pin')detail.append(dot(70,72,5,light),path('M70 68 L71 71 L74 72 L71 73 L70 76 L69 73 L66 72 L69 71 Z',color));
    if(look.detail==='patch')detail.append(rect(20,74,15,9,3,light),line('M23 77 L32 80 M23 80 L32 77',color,1.5));
    group.append(detail);
    const neck=svg('g',{'data-slot':'neck'});
    if(look.neck==='bandana')neck.append(path('M28 70 Q50 75 72 70 L50 87 Z'),line('M35 73 Q50 78 65 73',light,1.6));
    if(look.neck==='scarf')neck.append(rect(24,71,52,7,3),path('M63 76 H73 L71 95 H62 Z'),line('M64 91 H71',light,1.5));
    if(look.neck==='tie')neck.append(path('M45 70 H55 L53 76 L58 87 L50 94 L42 87 L47 76 Z'),line('M47 73 H53',light,1.5));
    if(look.neck==='bowtie')neck.append(path('M34 69 Q32 74 34 79 L49 75 L66 79 Q68 74 66 69 L51 73 Z'),dot(50,74,3),line('M37 72 L45 74 M63 72 L55 74',light,1.5));
    group.append(neck);
    const head=svg('g',{'data-slot':'head'});
    if(look.head==='cap')head.append(path('M27 23 Q28 4 48 4 Q68 4 70 23 Z'),rect(25,20,53,6,3),line('M48 7 V18',light,1.5));
    if(look.head==='antenna')head.append(line('M50 21 V8',color,3),dot(50,6,5,color),dot(49,4,1.5));
    if(look.head==='beanie')head.append(path('M23 23 Q26 4 50 4 Q74 4 77 23 Z'),rect(22,19,56,8,3),dot(50,3,5,color),line('M31 22 H69',light,1.5));
    if(look.head==='beret')head.append(path('M21 20 Q17 4 48 5 Q75 -1 81 16 Q72 24 24 23 Z'),rect(27,20,47,5,2),line('M55 6 L58 2',color,3));
    if(look.head==='hat')head.append(path('M30 21 L34 4 Q40 8 50 7 Q60 8 66 4 L70 21 Z'),rect(20,20,60,6,3),line('M33 17 H67',light,3));
    if(look.head==='headphones')head.append(line('M13 46 V35 Q13 12 50 12 Q87 12 87 35 V46',ink,6),rect(6,42,12,23,5),rect(82,42,12,23,5),line('M9 48 V58 M91 48 V58',light,2));
    group.append(head);
    const glasses=svg('g',{'data-slot':'glasses'});
    if(look.glasses==='rectangle')glasses.append(line('M23 45 H44 V59 H23 Z M56 45 H77 V59 H56 Z M44 50 H56',ink,3));
    if(look.glasses==='round')glasses.append(svg('circle',{cx:35,cy:51,r:11,fill:'none',stroke:ink,'stroke-width':3}),svg('circle',{cx:65,cy:51,r:11,fill:'none',stroke:ink,'stroke-width':3}),line('M46 49 H54',ink,3));
    if(look.glasses==='sunglasses')glasses.append(path('M21 44 H45 L42 58 Q31 64 25 57 Z M55 44 H79 L75 57 Q69 64 58 58 Z',ink),line('M43 48 H57',ink,3),line('M29 47 L35 52 M62 47 L68 52',light,2));
    if(look.glasses==='visor')glasses.append(svg('rect',{x:20,y:42,width:60,height:19,rx:8,fill:color,'fill-opacity':.45,stroke:ink,'stroke-width':2.5}),line('M27 47 H52',light,2));
    group.append(glasses);
    return group;
  }
};
