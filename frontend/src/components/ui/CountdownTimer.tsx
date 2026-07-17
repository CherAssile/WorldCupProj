import { useEffect, useState } from "react";

interface CountdownTimerProps {
  target: Date;
  label?: string;
}

function TimeUnit({ value, unit }: { value: string; unit: string }) {
  return (
    <div className="text-center">
      <div className="num text-[30px] font-extrabold text-accent md:text-[26px]">{value}</div>
      <div className="text-[9px] tracking-[0.1em] text-ink-muted md:hidden">{unit}</div>
    </div>
  );
}

/** Compte à rebours jusqu'au verrouillage d'un match (kickoff_at). Empilé sur mobile, en ligne sur desktop. */
export function CountdownTimer({ target, label = "Verrouillage dans" }: CountdownTimerProps) {
  const [remainingMs, setRemainingMs] = useState(() => Math.max(0, target.getTime() - Date.now()));

  useEffect(() => {
    const interval = setInterval(() => {
      setRemainingMs(Math.max(0, target.getTime() - Date.now()));
    }, 1000);
    return () => clearInterval(interval);
  }, [target]);

  const totalSeconds = Math.floor(remainingMs / 1000);
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");

  return (
    <div className="flex-1 rounded-2xl bg-[rgba(11,18,32,0.6)] p-3.5 md:flex md:items-center md:justify-between md:px-5 md:py-3.5">
      <div className="mb-2.5 text-center text-[10px] font-bold uppercase tracking-[0.1em] text-ink-secondary md:mb-0 md:text-left md:text-[11px]">
        {label}
      </div>
      <div className="flex items-center justify-center gap-2.5 md:gap-2">
        <TimeUnit value={hours} unit="H" />
        <span className="-mt-2 text-[22px] font-extrabold text-[#2E3C57] md:mt-0">:</span>
        <TimeUnit value={minutes} unit="MIN" />
        <span className="-mt-2 text-[22px] font-extrabold text-[#2E3C57] md:mt-0">:</span>
        <TimeUnit value={seconds} unit="SEC" />
      </div>
    </div>
  );
}
