export interface PhaseTabDef<T extends string> {
  id: T;
  label: string;
}

interface PhaseTabsProps<T extends string> {
  tabs: PhaseTabDef<T>[];
  value: T;
  onChange: (value: T) => void;
}

export function PhaseTabs<T extends string>({ tabs, value, onChange }: PhaseTabsProps<T>) {
  return (
    <div className="flex gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {tabs.map((tab) => {
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
