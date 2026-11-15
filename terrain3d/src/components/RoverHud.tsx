import type { RoverTelemetry } from "./RoverVehicle";
import type { RoverProfile } from "../geometry/roverPhysics";
import { MER_REFERENCE } from "../geometry/roverPhysics";
import type { ValidatedTerrainData } from "../types/terrain";
import { MerArchiveStudy } from "./MerArchiveStudy";
import { useEffect, useState } from "react";

export function RoverHud({ telemetry: t, terrain, profile, timeScale, grip, tractionControl, setProfile, setTimeScale, setGrip, setTractionControl, onRecover }: {
  telemetry:RoverTelemetry|null;terrain:ValidatedTerrainData;profile:RoverProfile;timeScale:number;grip:number;tractionControl:boolean;
  setProfile:(profile:RoverProfile)=>void;setTimeScale:(rate:number)=>void;setGrip:(grip:number)=>void;setTractionControl:(enabled:boolean)=>void;onRecover:()=>void;
}) {
  const [setupOpen,setSetupOpen]=useState(()=>window.innerWidth>600);
  const sourceSpacing=typeof terrain.resolutionMeters==="number"?terrain.resolutionMeters.toLocaleString():`${terrain.resolutionMeters.x.toLocaleString()} × ${terrain.resolutionMeters.y.toLocaleString()}`;
  useEffect(()=>{const query=window.matchMedia("(min-width:601px)");const update=()=>setSetupOpen(query.matches);query.addEventListener("change",update);return()=>query.removeEventListener("change",update);},[]);
  const status=t?.error?"PHYSICS UNAVAILABLE":t?.loading||!t?"INITIALIZING PHYSICS":t.overturned?"ROLLOVER · RECOVER VEHICLE":t.boundaryBlocked?"GEOFENCE HOLD":Math.abs(t.roll)>20?"CROSS-SLOPE CAUTION":(t.contacts<4?"LIMITED GROUND CONTACT":"SURFACE CONTACT NOMINAL");
  return <section className="rover-console" aria-label="Rover instruments" data-warning={!!t?.error||t?.overturned||t?.boundaryBlocked||Math.abs(t?.roll??0)>20}>
    <div className="rover-console-heading"><span><i /> SURFACE OPERATIONS</span><strong role="status">{status}</strong></div>
    <div className="rover-console-main">
      <div className="rover-speed"><span>GROUND SPEED</span><strong>{Math.abs(t?.speed??0).toFixed(3)}<small>m/s</small></strong><em>{(t?.speed??0)<-.005?"REVERSE":"FORWARD"} / {profile==="mer"?"MER LIMIT":"TRAINING"}</em></div>
      <div className="rover-attitude" aria-label="Rover attitude"><div className="rover-horizon"><div style={{transform:`translateY(${Math.max(-20,Math.min(20,t?.pitch??0))}px) rotate(${-Math.max(-70,Math.min(70,t?.roll??0))}deg)`}} /><span>⌖</span></div><span>P { (t?.pitch??0).toFixed(1)}°<b />R {(t?.roll??0).toFixed(1)}°</span></div>
      <div className="rover-contact"><span>CONTACT <b>{t?.contacts??0}/6</b></span><div className="wheel-loads">{[0,1,2].map(row=><div key={row}>{[row,row+3].map(i=><i key={i} data-contact={(t?.loads[i]??0)>0} title={`Wheel ${i+1}: ${Math.round(t?.loads[i]??0)} N estimated suspension load`}><span style={{height:`${Math.max(5,Math.min(100,25+(t?.suspension[i]??0)*100))}%`}} /></i>)}</div>)}</div><small>SUSPENSION TRAVEL</small></div>
      <dl className="rover-numbers"><div><dt>ODOMETER</dt><dd>{(t?.distance??0).toFixed(1)} <small>m</small></dd></div><div><dt>STEERING</dt><dd>{(t?.steer??0).toFixed(1)}<small>°</small></dd></div><div><dt>GRIP DEMAND</dt><dd>{Math.round(Math.min(999,(t?.traction??0)*100))}<small>%</small></dd></div></dl>
    </div>
    <details className="rover-setup-section" open={setupOpen} onToggle={event=>setSetupOpen(event.currentTarget.open)}><summary>Drive setup <span>{profile==="mer"?"MER":"TRAINING"} · {timeScale}×</span></summary><div className="rover-setup">
      <label>Drive profile<select aria-label="Rover drive profile" value={profile} onChange={e=>{const next=e.target.value as RoverProfile;setProfile(next);setTimeScale(next==="mer"?10:1);}}><option value="mer">MER reference · 0.05 m/s</option><option value="training">Training · 1.8 m/s</option></select></label>
      <label>Time<select aria-label="Simulation time scale" value={timeScale} onChange={e=>setTimeScale(Number(e.target.value))}><option value={1}>1× real time</option><option value={5}>5×</option><option value={10}>10×</option><option value={20}>20×</option></select></label>
      <label>Grip preset<select aria-label="Rover surface grip" value={grip} onChange={e=>setGrip(Number(e.target.value))}><option value={.95}>Firm · μ 0.95</option><option value={.65}>Regolith · μ 0.65</option><option value={.35}>Loose · μ 0.35</option></select></label>
      <button type="button" aria-pressed={tractionControl} onClick={()=>setTractionControl(!tractionControl)}>TCS {tractionControl?"ON":"OFF"}</button>
      <button type="button" onClick={onRecover}>Recover rover</button>
    </div></details>
    <p className="rover-controls">W / S drive · A / D steer · Space brake · Shift creep · {profile==="mer"?"MER hill hold · ":""}Drag camera</p>
    <details className="rover-reference"><summary>MER reference & terrain fidelity</summary><div>
      <p><strong>{MER_REFERENCE.massKg} kg · six wheels · Ø {(MER_REFERENCE.wheelRadiusM*200).toFixed(1)} cm.</strong> Geometry and mass reference Spirit / Opportunity; suspension, tire grip and motor response are engineering approximations.</p>
      <p>{terrain.dataType==="real"?"Measured DEM":"Synthetic terrain"} · source spacing {sourceSpacing} m · physical relief 1×. Coarse elevation grids do not resolve wheel-scale rocks or soil. Grip presets are simulation inputs, not measured soil properties.</p>
      <p>No MER traverse is loaded for this terrain. Sol/site/drive indices require the matching mission location and product labels; they are not distances or wheel-slip telemetry.</p>
      <nav aria-label="MER data sources"><a href="https://an.rsl.wustl.edu/mer/" target="_blank" rel="noreferrer">Analyst’s Notebook ↗</a><a href="https://pds-geosciences.wustl.edu/missions/mer/geo_mer_datasets.htm" target="_blank" rel="noreferrer">PDS products & labels ↗</a><a href={MER_REFERENCE.source} target="_blank" rel="noreferrer">JPL wheel reference ↗</a><a href={MER_REFERENCE.speedSource} target="_blank" rel="noreferrer">PDS rover description ↗</a></nav>
      <MerArchiveStudy />
    </div></details>
    {t?.error&&<p role="alert">{t.error}</p>}
  </section>;
}
