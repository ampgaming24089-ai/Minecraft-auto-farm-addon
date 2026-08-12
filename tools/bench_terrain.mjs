import { SECTOR, BEDROCK_Y, SEA_LEVEL, biomeAt, heightAt, caveFloorAt, crustAt, isWithinWorld }
  from "/home/user/Minecraft-auto-farm-addon/BP/scripts/world/biomes.js";

function rectangles(keyAt) {
  const used = new Uint8Array(SECTOR*SECTOR); const out = [];
  for (let lz=0; lz<SECTOR; lz++) for (let lx=0; lx<SECTOR; lx++) {
    const i = lz*SECTOR+lx; if (used[i]) continue;
    const k = keyAt(lx,lz); if (k===null) { used[i]=1; continue; }
    let w=1; while (lx+w<SECTOR && !used[i+w] && keyAt(lx+w,lz)===k) w++;
    let h=1;
    grow: while (lz+h<SECTOR) { for (let dx=0; dx<w; dx++) { const j=(lz+h)*SECTOR+lx+dx;
      if (used[j] || keyAt(lx+dx,lz+h)!==k) break grow; } h++; }
    for (let dz=0; dz<h; dz++) for (let dx=0; dx<w; dx++) used[(lz+dz)*SECTOR+lx+dx]=1;
    out.push({lx,lz,w,h});
  }
  return out;
}

function cost(x0, z0) {
  const height=new Int16Array(SECTOR*SECTOR), floor=new Int16Array(SECTOR*SECTOR),
        crust=new Int16Array(SECTOR*SECTOR), biome=new Array(SECTOR*SECTOR);
  for (let lz=0; lz<SECTOR; lz++) for (let lx=0; lx<SECTOR; lx++) {
    const i=lz*SECTOR+lx, x=x0+lx, z=z0+lz;
    if (!isWithinWorld({x,z})) { height[i]=-1; continue; }
    const b=biomeAt(x,z); biome[i]=b; height[i]=heightAt(x,z,b);
    floor[i]=caveFloorAt(x,z); crust[i]=crustAt(x,z);
  }
  const A = rectangles((lx,lz)=>{const i=lz*SECTOR+lx; return height[i]<0?null:`${floor[i]}:${biome[i].id}`;});
  const B = rectangles((lx,lz)=>{const i=lz*SECTOR+lx; return height[i]<0?null:`${height[i]}:${crust[i]}:${biome[i].id}`;});
  const C = rectangles((lx,lz)=>{const i=lz*SECTOR+lx; return (height[i]<0||height[i]>=SEA_LEVEL)?null:"sea";});
  // blocks actually written
  let blocks=0;
  for (let i=0;i<SECTOR*SECTOR;i++) {
    if (height[i]<0) continue;
    const cf=floor[i], h=height[i], bottom=Math.max(cf+2, h-crust[i]);
    blocks += 1 + (cf-BEDROCK_Y) + Math.max(0, h-bottom+1);
    if (h < SEA_LEVEL) blocks += SEA_LEVEL-h;
  }
  return { calls: A.length*3 + B.length*2 + C.length + 4 + 14, blocks, A:A.length, B:B.length, C:C.length };
}

let calls=0, blocks=0, worst=0, worstB=0;
const N=60;
for (let i=0;i<N;i++) {
  const sx=(i*137)%6000-3000, sz=(i*251)%6000-3000;
  const c=cost(sx*SECTOR, sz*SECTOR);
  calls+=c.calls; blocks+=c.blocks; worst=Math.max(worst,c.calls); worstB=Math.max(worstB,c.blocks);
}
console.log(`sampled ${N} sectors of the NEW world`);
console.log(`  fill calls/sector : avg ${(calls/N).toFixed(0)}  worst ${worst}`);
console.log(`  blocks written    : avg ${(blocks/N/1000).toFixed(1)}k  worst ${(worstB/1000).toFixed(1)}k`);
console.log(`  (old 12-block slab wrote ~13k blocks/sector in ~253 parsed commands)`);
