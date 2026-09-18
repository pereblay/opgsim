export default function(component) {
  const {parentElement, data, setStateValue, setTriggerValue} = component;
  const root=parentElement.querySelector('.exercise-root');
  const canvas=root.querySelector('canvas'), ctx=canvas.getContext('2d');
  const tool=root.querySelector('[data-tool]'), readout=root.querySelector('[data-readout]');
  const status=root.querySelector('[data-status]');
  const ex=data.exercise;
  let scene=structuredClone(data.scene || {placements:{},rays:[],draft:[],tool:'place:object'});
  scene.placements ||= {}; scene.rays ||= []; scene.draft ||= []; scene.tool ||= 'place:object';
  let cursor=null, timer=null, width=1000, height=490;
  let zoom=scene.zoom||1;
  const colors=['#2563eb','#d97706','#16816b'];
  const options=[['place:object','Colocar objeto O'],...ex.elements.map(e=>['place:'+e.name,'Colocar '+e.name+' · '+e.kind]),...ex.rays.map(r=>['ray:'+r.id,r.label])];
  tool.replaceChildren(...options.map(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;}));
  tool.value=scene.tool;
  const bounds=()=>{const center=(ex.xmin+ex.xmax)/2, half=(ex.xmax-ex.xmin)/2/zoom;return {xmin:center-half,xmax:center+half,ymin:-38/zoom,ymax:38/zoom};};
  const sx=x=>{const b=bounds();return 45+(x-b.xmin)/(b.xmax-b.xmin)*(width-65);};
  const sy=y=>{const b=bounds();return 25+(b.ymax-y)/(b.ymax-b.ymin)*(height-65);};
  const world=(event)=>{const rect=canvas.getBoundingClientRect(),b=bounds();return [b.xmin+((event.clientX-rect.left)*width/rect.width-45)/(width-65)*(b.xmax-b.xmin),b.ymax-((event.clientY-rect.top)*height/rect.height-25)/(height-65)*(b.ymax-b.ymin)];};
  function save(){scene.zoom=zoom;setStateValue('value',structuredClone(scene));}
  function snap(p) {
    if(scene.tool.startsWith('place:')) return [Math.round(p[0]),0];
    let result=p, best=10;
    const consider=q=>{const d=Math.hypot(sx(q[0])-sx(p[0]),sy(q[1])-sy(p[1]));if(d<best){best=d;result=q;}};
    if(scene.placements.object){consider([scene.placements.object[0],ex.object_height]);consider([scene.placements.object[0],0]);}
    if(root.querySelector('[data-snap]').checked){
      for(let i=0;i<ex.elements.length;i++){
        const e=ex.elements[i], pos=scene.placements[e.name];if(!pos)continue;
        if(Math.abs(p[1])>e.aperture/2)continue;
        const shape=ex.shapes[i];
        // Interpolate each sampled cap at the pointer's height; no ray solution is used.
        for(let j=1;j<shape.length;j++){
          const a=shape[j-1],b=shape[j];
          if(Math.abs(a[1]-b[1])<1e-10 || (p[1]-a[1])*(p[1]-b[1])>0)continue;
          const t=(p[1]-a[1])/(b[1]-a[1]);consider([pos[0]+a[0]+t*(b[0]-a[0]),p[1]]);
        }
      }
    }
    return result;
  }
  function path(points,color,dashed=false,lineWidth=2){if(!points.length)return;ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=lineWidth;ctx.setLineDash(dashed?[6,4]:[]);points.forEach((p,i)=>i?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])));ctx.stroke();ctx.setLineDash([]);}
  function dot(p,color,r=3){ctx.beginPath();ctx.fillStyle=color;ctx.arc(sx(p[0]),sy(p[1]),r,0,2*Math.PI);ctx.fill();}
  function text(txt,p,color='#334155'){ctx.fillStyle=color;ctx.fillText(txt,sx(p[0])+5,sy(p[1])-7);}
  function draw(){
    ctx.clearRect(0,0,width,height);ctx.fillStyle='#ffffff';ctx.fillRect(0,0,width,height);ctx.font='12px system-ui';
    const b=bounds();const gx=zoom>1.5?5:10,gy=zoom>1.5?1:2;
    for(let x=Math.ceil(b.xmin/gx)*gx;x<=b.xmax;x+=gx){path([[x,b.ymin],[x,b.ymax]],'#e7edf4',false,1);if(Math.round(x/gx)%5===0){ctx.fillStyle='#64748b';ctx.fillText(x.toFixed(0),sx(x)-10,height-12);}}
    for(let y=Math.ceil(b.ymin/gy)*gy;y<=b.ymax;y+=gy){path([[b.xmin,y],[b.xmax,y]],'#e7edf4',false,1);if(Math.round(y/gy)%5===0){ctx.fillStyle='#64748b';ctx.fillText(y.toFixed(0),4,sy(y)+4);}}
    path([[b.xmin,0],[b.xmax,0]],'#64748b',false,1.5);
    ctx.fillStyle='#334155';ctx.fillText('x (mm)',width-48,height-12);ctx.fillText('y (mm)',4,15);
    for(let i=0;i<ex.elements.length;i++){
      const e=ex.elements[i],position=scene.placements[e.name];if(!position)continue;
      const shape=ex.shapes[i].map(p=>[p[0]+position[0],p[1]]);
      if(!e.kind.startsWith('Espejo')){ctx.beginPath();shape.forEach((p,j)=>j?ctx.lineTo(sx(p[0]),sy(p[1])):ctx.moveTo(sx(p[0]),sy(p[1])));ctx.fillStyle='#dff2fb';ctx.fill();}
      path(shape,e.kind.startsWith('Espejo')?'#475569':'#0284c7',false,2.5);text(e.name,[position[0],e.aperture/2+1]);
    }
    if(scene.placements.object){const x=scene.placements.object[0];path([[x,0],[x,ex.object_height]],'#18263c',false,4);dot([x,ex.object_height],'#18263c',4);text('O',[x,ex.object_height]);}
    for(const ray of scene.rays){const i=ex.rays.findIndex(r=>r.id===ray.id);path(ray.points,colors[Math.max(0,i)%3]);for(const p of ray.points)dot(p,colors[Math.max(0,i)%3],2.5);}
    if(scene.draft.length){const i=ex.rays.findIndex(r=>'ray:'+r.id===scene.tool);const color=colors[Math.max(0,i)%3];path(scene.draft,color);for(const p of scene.draft)dot(p,color);if(cursor)path([scene.draft.at(-1),cursor],color,true);}
    if(cursor){dot(cursor,'#111827',3);if(scene.tool.startsWith('place:'))path([[cursor[0],b.ymin],[cursor[0],b.ymax]],'#94a3b8',true,1);}
    status.textContent=`${Object.keys(scene.placements).length}/${ex.elements.length+1} posiciones · ${scene.rays.length}/${ex.rays.length} rayos terminados`+(scene.draft.length?` · ${scene.draft.length} puntos en el rayo actual`:'');
  }
  function showCursor(p){cursor=snap(p);const prev=scene.draft.at(-1);let msg=`x = ${cursor[0].toFixed(2)} mm · altura y = ${cursor[1].toFixed(2)} mm`;
    if(prev){const dx=cursor[0]-prev[0],dy=cursor[1]-prev[1];msg+=` · Δx = ${dx.toFixed(2)} · Δy = ${dy.toFixed(2)} mm · ángulo / +x = ${(Math.atan2(dy,dx)*180/Math.PI).toFixed(2)}°`;}
    readout.textContent=msg;draw();
  }
  function addPoint(p){if(!scene.draft.length||Math.hypot(p[0]-scene.draft.at(-1)[0],p[1]-scene.draft.at(-1)[1])>.15)scene.draft.push([...p]);}
  function placeOrPoint(p,finish=false){
    if(scene.tool.startsWith('place:')){
      const name=scene.tool.slice(6);scene.placements[name]=[Math.round(p[0]),0];scene.rays=[];scene.draft=[];
      const next=options.find(([value])=>value.startsWith('place:')&&!scene.placements[value.slice(6)]);
      scene.tool=next?next[0]:'ray:'+ex.rays[0].id;tool.value=scene.tool;
    }else{
      if(Object.keys(scene.placements).length!==ex.elements.length+1){readout.textContent='Coloca primero el objeto y todos los elementos.';return;}
      addPoint(p);
      if(finish&&scene.draft.length>=2){scene.rays=scene.rays.filter(r=>r.id!==scene.tool.slice(4));scene.rays.push({id:scene.tool.slice(4),points:structuredClone(scene.draft)});scene.draft=[];}
    }
    save();draw();
  }
  canvas.onpointermove=e=>showCursor(world(e));
  canvas.onpointerleave=()=>{cursor=null;draw();};
  canvas.onclick=e=>{canvas.focus();if(e.detail>1)return;const p=snap(world(e));clearTimeout(timer);timer=setTimeout(()=>placeOrPoint(p),230);};
  canvas.ondblclick=e=>{e.preventDefault();clearTimeout(timer);placeOrPoint(snap(world(e)),true);};
  tool.onchange=()=>{clearTimeout(timer);scene.tool=tool.value;scene.draft=[];save();draw();};
  root.querySelector('[data-undo]').onclick=()=>{clearTimeout(timer);if(scene.draft.length)scene.draft.pop();else if(scene.rays.length){const ray=scene.rays.pop();scene.tool='ray:'+ray.id;tool.value=scene.tool;scene.draft=ray.points.slice(0,-1);}save();draw();};
  root.querySelector('[data-delete]').onclick=()=>{scene.rays=scene.rays.filter(r=>'ray:'+r.id!==scene.tool);scene.draft=[];save();draw();};
  root.querySelector('[data-reset]').onclick=()=>{clearTimeout(timer);cursor=null;scene={placements:{},rays:[],draft:[],tool:'place:object',zoom:1};zoom=1;tool.value=scene.tool;save();draw();};
  root.querySelector('[data-finish]').onclick=()=>{clearTimeout(timer);save();setTriggerValue('submitted',structuredClone(scene));};
  root.querySelector('[data-end-ray]').onclick=()=>{if(scene.draft.length>=2){scene.rays=scene.rays.filter(r=>r.id!==scene.tool.slice(4));scene.rays.push({id:scene.tool.slice(4),points:structuredClone(scene.draft)});scene.draft=[];save();draw();}};
  for(const name of ['snap'])root.querySelector(`[data-${name}]`).onchange=()=>{scene[name]=root.querySelector(`[data-${name}]`).checked;save();draw();};
  root.querySelector('[data-snap]').checked=scene.snap??true;
  root.querySelector('[data-zoom-in]').onclick=()=>{zoom=Math.min(4,zoom*1.4);save();draw();};
  root.querySelector('[data-zoom-out]').onclick=()=>{zoom=Math.max(.5,zoom/1.4);save();draw();};
  canvas.onkeydown=e=>{if(e.key==='Escape'){scene.draft=[];save();draw();}else if(e.key==='Backspace'){e.preventDefault();root.querySelector('[data-undo]').click();}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const p=cursor||[0,0];showCursor([p[0]+(e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0),p[1]+(e.key==='ArrowUp'?.25:e.key==='ArrowDown'?-.25:0)]);}else if(e.key==='Enter'&&cursor){e.preventDefault();placeOrPoint(cursor,e.shiftKey);}};
  const resize=()=>{width=Math.max(320,root.clientWidth);const dpr=window.devicePixelRatio||1;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);canvas.style.width='100%';canvas.style.height=height+'px';ctx.setTransform(dpr,0,0,dpr,0,0);draw();};
  const observer=new ResizeObserver(resize);observer.observe(root);resize();
  return ()=>{clearTimeout(timer);observer.disconnect();};
}
