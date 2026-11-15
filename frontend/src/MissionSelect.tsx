import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

type Option = { value: string; label: string };
export function MissionSelect({ label, value, options, onChange }: { label: string; value: string; options: Option[]; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    const dismiss = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  useEffect(() => { setOpen(false); }, [value]);
  useEffect(() => { if (open) document.getElementById(`${id}-${active}`)?.scrollIntoView({ block: "nearest" }); }, [open, active, id]);
  const show = () => { setActive(Math.max(0, options.findIndex(option => option.value === value))); setOpen(true); };
  return <div className="mission-select" ref={root} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false); }}>
    <span className="select-label" id={`${id}-label`}>{label}</span>
    <button type="button" className="select-trigger" role="combobox" aria-labelledby={`${id}-label`} aria-controls={`${id}-list`} aria-haspopup="listbox" aria-expanded={open}
      aria-activedescendant={open ? `${id}-${active}` : undefined} disabled={!options.length}
      onClick={() => open ? setOpen(false) : show()} onKeyDown={event => {
        if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          if (!open) { show(); return; }
          setActive(current => event.key === "Home" ? 0 : event.key === "End" ? options.length - 1 : (current + (event.key === "ArrowDown" ? 1 : -1) + options.length) % options.length);
        } else if ((event.key === "Enter" || event.key === " ") && open) {
          event.preventDefault(); if (options[active]) onChange(options[active].value); setOpen(false);
        } else if (event.key === "Escape") { event.preventDefault(); setOpen(false); }
      }}><span>{options.find(option => option.value === value)?.label ?? "Loading…"}</span><ChevronDown size={16} /></button>
    {open && <div className="select-options" id={`${id}-list`} role="listbox" aria-labelledby={`${id}-label`}>
      {options.map((option, index) => <div key={option.value} role="option" id={`${id}-${index}`} aria-selected={option.value === value}
        className={`select-option ${active === index ? "highlighted" : ""}`} onPointerMove={() => setActive(index)}
        onMouseDown={event => event.preventDefault()} onClick={() => { onChange(option.value); setOpen(false); }}>
        <span>{option.label}</span>{option.value === value && <Check size={15} />}
      </div>)}
    </div>}
  </div>;
}
