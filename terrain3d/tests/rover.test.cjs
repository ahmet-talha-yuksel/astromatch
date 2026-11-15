const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const path=require('node:path');
const THREE=require('three');
const {validateTerrainData}=require('../.test-build/validation/terrain.js');
const {explorationWorld}=require('../.test-build/geometry/explorationWorld.js');
const {RoverPhysics,loadRoverBackend,ROVER_STEP,MER_REFERENCE}=require('../.test-build/geometry/roverPhysics.js');
const {SURFACE_GRAVITY}=require('../.test-build/geometry/jumpPhysics.js');
const base=JSON.parse(readFileSync(path.join(__dirname,'../public/terrain/mars_demo.json'),'utf8'));
const idle={throttle:0,steer:0,brake:false,creep:false,grip:.65,tractionControl:true,profile:'mer'};
function terrain(body='Mars',height=()=>0,span=20,n=81){
 const heights=Array.from({length:n*n},(_,i)=>height((i%n)/(n-1)*span-span/2,Math.floor(i/n)/(n-1)*span-span/2));
 return validateTerrainData({...base,body,width:n,height:n,heights,validMask:heights.map(v=>v!==null),cellSizeMeters:span/(n-1),resolutionMeters:span/(n-1),horizontalWindowMeters:{width:span,height:span}});
}
async function setup(body='Mars',height,span,n){const t=terrain(body,height,span,n),world=explorationWorld(t,1);return new RoverPhysics(await loadRoverBackend(),t,world,world.scale,{u:.5,v:.5});}
function run(sim,input=idle,seconds=2){for(let i=0;i<Math.round(seconds/ROVER_STEP);i++)sim.step(input);return sim.snapshot();}
test('MER reference uses documented mass and wheel diameter; six contacts support the chassis',async()=>{
 const sim=await setup();try{
  const s=run(sim,idle,4);
  assert.equal(sim.body.mass(),185);assert.equal(MER_REFERENCE.wheelRadiusM,.131);assert.equal(sim.vehicle.numWheels(),6);
  assert.equal(s.contacts,6);assert.ok(Math.abs(s.pitch)<.3&&Math.abs(s.roll)<.3);
  const weight=s.wheels.reduce((sum,w)=>sum+w.loadN,0);
  assert.ok(Math.abs(weight-185*SURFACE_GRAVITY.Mars)/(185*SURFACE_GRAVITY.Mars)<.15,weight);
  assert.ok(Math.abs(s.speed)<.01);
 }finally{sim.dispose();}
});
test('throttle drives forward, steering changes heading, braking stops rather than teleports',async()=>{
 const sim=await setup();try{
  run(sim,idle,2);const start=sim.snapshot().position.clone();
  const a=run(sim,{...idle,profile:'training',throttle:1},2);
  assert.ok(a.speed>.6&&a.position.z<start.z);
  const firstHeading=new THREE.Vector3(0,0,-1).applyQuaternion(a.rotation);
  const b=run(sim,{...idle,profile:'training',throttle:1,steer:.6},1);
  assert.ok(firstHeading.distanceTo(new THREE.Vector3(0,0,-1).applyQuaternion(b.rotation))>.02);
  const before=b.position.clone();const stopped=run(sim,{...idle,profile:'training',brake:true},2);
  assert.ok(Math.abs(stopped.speed)<.05);assert.ok(stopped.position.distanceTo(before)>0);
 }finally{sim.dispose();}
});
test('fixed-step suspension follows a measured ramp and MER hill hold prevents creeping',async()=>{
 const sim=await setup('Mars',(_x,z)=>z*Math.tan(15*Math.PI/180));try{
  const settled=run(sim,idle,4);
  assert.ok(Math.abs(Math.abs(settled.pitch)-15)<2,settled.pitch);assert.ok(Math.abs(settled.roll)<1);
  assert.equal(settled.contacts,6);assert.ok(Math.abs(settled.speed)<.03,settled.speed);
  const driving=run(sim,{...idle,throttle:1},3);
  assert.ok(driving.speed>0&&driving.speed<.075,driving.speed);
 }finally{sim.dispose();}
});
test('each wheel suspension responds independently to uneven support',async()=>{
 const sim=await setup('Mars',(x,z)=>.08*Math.exp(-((x+.68)**2+(z+.62)**2)/.025),4,81);try{
  const s=run(sim,idle,4),lengths=s.wheels.map(w=>w.y);
  assert.ok(Math.max(...lengths)-Math.min(...lengths)>.015,lengths);
  assert.equal(s.contacts,6);assert.ok(s.wheels.every(w=>Number.isFinite(w.loadN)&&w.loadN>=0));
 }finally{sim.dispose();}
});
test('Moon braking distance increases with lower gravity and reduced normal load',async()=>{
 const distances=[];
 for(const body of ['Earth','Moon']){
  const sim=await setup(body);try{
   run(sim,idle,3);sim.body.setLinvel({x:0,y:0,z:-1.5},true);const start=sim.snapshot().position.z;
   let s;for(let i=0;i<600;i++){sim.step({...idle,profile:'training',brake:true});s=sim.snapshot();if(Math.abs(s.speed)<.03)break;}
   distances.push(Math.abs(s.position.z-start)/sim.sceneScale);
  }finally{sim.dispose();}
 }
 assert.ok(distances[1]>distances[0]*1.5,distances);
});
test('NoData and parcel geofences reject unsafe travel without filling missing geometry',async()=>{
 const sim=await setup('Mars',(x,z)=>z<-2&&Math.abs(x)<2?null:0,12,81);try{
  run(sim,idle,2);const s=run(sim,{...idle,profile:'training',throttle:1},12);
  assert.ok(s.boundaryBlocked);assert.ok(s.position.z/sim.sceneScale>-2);
  assert.ok(Number.isFinite(s.position.y));
 }finally{sim.dispose();}
});
test('chassis retains free rotation and recover restores an overturned rover',async()=>{
 const sim=await setup();try{
  run(sim,idle,2);const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),2);
  sim.body.setRotation(q,true);assert.ok(sim.snapshot().overturned);
  sim.reset({u:.5,v:.5},0);const s=run(sim,idle,2);assert.ok(!s.overturned&&Math.abs(s.roll)<1);
 }finally{sim.dispose();}
});
test('fixed-step accumulation gives the same physical trajectory at 30, 60 and 144 render FPS',async()=>{
 const samples=[];
 for(const fps of [30,60,144]){
  const sim=await setup();try{
   run(sim,idle,1);let accumulator=0;
   for(let frame=0;frame<fps;frame++){
    accumulator+=1/fps;
    while(accumulator+1e-10>=ROVER_STEP){sim.step({...idle,profile:'training',throttle:1,steer:.3});accumulator=Math.max(0,accumulator-ROVER_STEP);}
   }
   samples.push(sim.snapshot());
  }finally{sim.dispose();}
 }
 for(const sample of samples.slice(1)){
  assert.ok(sample.position.distanceTo(samples[0].position)<1e-8);
  assert.ok(sample.rotation.angleTo(samples[0].rotation)<1e-6);
 }
});
test('normalizing a different DEM window never rescales wheel dimensions, gravity or vehicle speed',async()=>{
 const samples=[];
 for(const span of [20,200]){
  const sim=await setup('Mars',()=>0,span);try{
   const original=JSON.stringify(sim.terrain);run(sim,idle,2);
   const s=run(sim,{...idle,profile:'training',throttle:1},2);
   samples.push({distance:s.position.z/sim.sceneScale,speed:s.speed});
   assert.equal(JSON.stringify(sim.terrain),original);
   assert.equal(sim.vehicle.wheelRadius(0),Math.fround(.131));
  }finally{sim.dispose();}
 }
 assert.ok(Math.abs(samples[0].distance-samples[1].distance)<.005,JSON.stringify(samples));
 assert.ok(Math.abs(samples[0].speed-samples[1].speed)<.005);
});
test('forward, lift-off and continuous reverse input give smooth, bounded motion in both profiles on every planet',async()=>{
 for(const body of ['Earth','Mars','Moon']) for(const profile of ['mer','training']){
  const sim=await setup(body,()=>0,60);try{
   run(sim,idle,3);
   const drive={...idle,profile},minimum=profile==='mer'?.035:1.3,maximum=profile==='mer'?.065:1.95;
   let previous=0,largestStep=0;
   const sample=(input,seconds)=>{
    let s;
    for(let i=0;i<Math.round(seconds/ROVER_STEP);i++){
     sim.step(input);s=sim.snapshot();largestStep=Math.max(largestStep,Math.abs(s.speed-previous));previous=s.speed;
     assert.ok(Math.abs(s.speed)<maximum,`${body}/${profile}: speed ${s.speed}`);
    }
    return s;
   };
   const forward=sample({...drive,throttle:1},3);
   assert.ok(forward.speed>minimum,`${body}/${profile}: forward ${forward.speed}`);
   const released=sample(drive,3);
   assert.ok(Math.abs(released.speed)<(profile==='mer'?.008:.04),`${body}/${profile}: lift-off ${released.speed}`);
   const reverse=sample({...drive,throttle:-1},3);
   assert.ok(reverse.speed < -minimum,`${body}/${profile}: reverse ${reverse.speed}`);
   const again=sample({...drive,throttle:1},6);
   assert.ok(again.speed>minimum,`${body}/${profile}: reverse-to-forward ${again.speed}`);
   assert.ok(largestStep<.08,`${body}: abrupt speed change ${largestStep}`);
  }finally{sim.dispose();}
 }
});
test('sustained downhill/uphill throttle does not pulse between full brake and drive',async()=>{
 for(const slope of [-12,12]) for(const direction of [-1,1]){
  const sim=await setup('Mars',(_x,z)=>z*Math.tan(slope*Math.PI/180),60);try{
   run(sim,idle,4);
   run(sim,{...idle,profile:'training',throttle:direction},5);
   const speeds=[];
   for(let i=0;i<120;i++){sim.step({...idle,profile:'training',throttle:direction});speeds.push(sim.snapshot().speed*direction);}
   assert.ok(Math.min(...speeds)>1.6,JSON.stringify({slope,direction,min:Math.min(...speeds)}));
   assert.ok(Math.max(...speeds)-Math.min(...speeds)<.05,`${slope}/${direction}: speed oscillation`);
  }finally{sim.dispose();}
 }
});
