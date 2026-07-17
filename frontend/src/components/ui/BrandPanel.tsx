/** Panneau de marque desktop pour l'écran de connexion (masqué sur mobile). */
export function BrandPanel() {
  return (
    <div className="relative hidden w-[46%] flex-shrink-0 flex-col justify-between overflow-hidden bg-[linear-gradient(165deg,#22A85A,#116E42)] p-12 md:flex">
      <svg
        width="420"
        height="420"
        viewBox="0 0 420 420"
        className="absolute -bottom-[120px] -right-[120px] opacity-[0.14]"
        fill="none"
        stroke="#fff"
        strokeWidth="2"
      >
        <circle cx="210" cy="210" r="160" />
        <circle cx="210" cy="210" r="52" />
        <path d="M210 50v320M50 210h320" />
      </svg>

      <div className="relative flex h-[60px] w-[60px] items-center justify-center rounded-[18px] bg-app/90">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2CC169" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
        </svg>
      </div>

      <div className="relative">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#0B1220]/70">Mundial Pronos</div>
        <h2 className="mt-3 text-[34px] font-extrabold leading-[1.15] tracking-tight text-[#06210F]">
          Pronostique chaque match. Grimpe au classement.
        </h2>
        <p className="mt-3.5 max-w-[360px] text-[15px] leading-relaxed text-[#06210F]/75">
          Score exact, duels contre l'IA, récompenses du tournoi. Tout se joue le soir, avant le coup d'envoi.
        </p>
      </div>
    </div>
  );
}
