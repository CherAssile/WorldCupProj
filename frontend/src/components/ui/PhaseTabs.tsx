export type Phase = "groupes" | "huitiemes" | "quarts" | "demies" | "finale";

interface PhaseTabDef {
  id: Phase;
  label: string;
}

const PHASE_TABS: PhaseTabDef[] = [
  { id: "groupes", label: "Groupes" },
  { id: "huitiemes", label: "8es" },
  { id: "quarts", label: "Quarts" },
  { id: "demies", label: "Demies" },
  { id: "finale", label: "Finale" },
];

interface PhaseTabsProps {
  value: Phase;
  onChange: (phase: Phase) => void;
}

export function PhaseTabs({ value, onChange }: PhaseTabsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {PHASE_TABS.map((tab) => {
        const isActive = tab.id === value;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex-shrink-0 whitespace-nowrap rounded-full border px-[18px] py-2.5 font-sans text-sm font-bold transition-colors ${
              isActive
                ? "border-primary bg-primary text-[#06210F] shadow-[0_6px_16px_rgba(34,168,90,0.3)]"
                : "border-line bg-transparent text-ink-secondary"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
