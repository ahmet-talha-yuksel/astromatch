import { MissionSelect } from "./MissionSelect";

export type ProfileDimension = {
  name: string; label: string; impact: string; rationale: string;
  target_value_or_summary: string | number | null; earth_value_or_summary: string | number | null;
  evidence_target: string | null; evidence_earth: string | null;
  confidence: string; note: string; sources: { title: string; url_or_doi: string | null }[];
};
export type ProfileResponse = { mission: string; dimensions: ProfileDimension[]; overall_confidence: string; data_status: string; disclaimer: string };

const missionOptions = [
  { value: "human_base", label: "Human base" },
  { value: "rover_ops", label: "Rover ops" },
  { value: "astrobiology", label: "Astrobiology" },
  { value: "analog_testing", label: "Analog testing" },
];
const names: Record<string, string> = {
  terrain: "Terrain", thermal: "Thermal", aridity_vegetation: "Aridity & vegetation",
  water_ice: "Water & ice", surface_material: "Surface material", illumination: "Illumination", dust_wind: "Dust & wind",
};
const sourceHref = (url: string | null) => !url ? null : /^https?:\/\//.test(url) ? url : url.startsWith("doi:") ? `https://doi.org/${url.slice(4)}` : /^10\.\d{4,9}\//.test(url) ? `https://doi.org/${url}` : null;

export function AnalogProfile({ mission, onMission, profile, loading }: { mission: string; onMission: (mission: string) => void; profile: ProfileResponse | null; loading: boolean }) {
  return <section className="analog-profile" aria-label="Analog profile">
    <div className="analog-profile-head"><div><p className="section-kicker">EVIDENCE PROFILE</p><h2>Analog profile</h2><p className="muted">A mission-oriented characterization, separate from the terrain score.</p></div>
      <MissionSelect label="MISSION" value={mission} onChange={onMission} options={missionOptions} />
    </div>
    {profile ? <><div className="profile-confidence">Data confidence <strong>{profile.overall_confidence}</strong>{profile.data_status === "mock" && <span>MOCK DATA</span>}</div>
      <div className="profile-dimensions">{profile.dimensions.map(item => <article className="profile-dimension" key={item.name}>
        <div className="profile-dimension-top"><h3>{names[item.name] ?? item.name}</h3><span className="profile-label">{item.label}</span><span className={`profile-impact impact-${item.impact}`}>{item.impact}</span></div>
        <p>{item.rationale}</p><details className="profile-evidence"><summary aria-label={`Evidence for ${names[item.name] ?? item.name}`} title={`${item.note} Sources: ${item.sources.map(source => source.title).join(", ") || "unavailable"}`}>ⓘ Evidence · {item.confidence}</summary>
          <div><span>Target: {item.target_value_or_summary ?? "Unavailable"}</span><span>Earth: {item.earth_value_or_summary ?? "Unavailable"}</span><span>{item.note}</span>
            {item.sources.map((source, index) => sourceHref(source.url_or_doi) ? <a key={index} href={sourceHref(source.url_or_doi)!} target="_blank" rel="noreferrer">{source.title}</a> : <span key={index}>{source.title}{source.url_or_doi ? ` · ${source.url_or_doi}` : ""}</span>)}</div>
        </details>
      </article>)}</div><p className="profile-disclaimer">{profile.disclaimer}</p></> : <p className="muted">{loading ? "Loading profile…" : "Select an Earth analog to view its profile."}</p>}
  </section>;
}
