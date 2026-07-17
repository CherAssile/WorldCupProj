interface NavItemDef {
  id: "accueil" | "matchs" | "classement" | "profil";
  label: string;
  icon: JSX.Element;
}

const NAV_ITEMS: NavItemDef[] = [
  {
    id: "accueil",
    label: "Accueil",
    icon: <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  },
  {
    id: "matchs",
    label: "Matchs",
    icon: (
      <>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
      </>
    ),
  },
  {
    id: "classement",
    label: "Classement",
    icon: <path d="M6 9H4a2 2 0 0 0 0 4h2M18 9h2a2 2 0 0 1 0 4h-2M6 4h12v9a6 6 0 0 1-12 0zM8 21h8M12 17v4" />,
  },
  {
    id: "profil",
    label: "Profil",
    icon: (
      <>
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>
    ),
  },
];

interface BottomNavProps {
  active: NavItemDef["id"];
  onChange?: (id: NavItemDef["id"]) => void;
}

export function BottomNav({ active, onChange }: BottomNavProps) {
  return (
    <nav className="grid grid-cols-4 border-t border-white/[0.08] bg-[#0D1424] px-3 pb-[22px] pt-3">
      {NAV_ITEMS.map((item) => {
        const isActive = item.id === active;
        return (
          <button
            key={item.id}
            onClick={() => onChange?.(item.id)}
            className={`flex flex-col items-center gap-[5px] ${isActive ? "text-primary" : "text-ink-secondary"}`}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {item.icon}
            </svg>
            <span className={`text-[10px] ${isActive ? "font-bold" : "font-semibold"}`}>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
