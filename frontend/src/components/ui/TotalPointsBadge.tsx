interface TotalPointsBadgeProps {
  points: number;
}

export function TotalPointsBadge({ points }: TotalPointsBadgeProps) {
  return (
    <div className="num flex items-center gap-[7px] rounded-2xl bg-gradient-to-br from-accent-light to-accent-dark px-[13px] py-[9px] text-[15px] font-extrabold text-[#2A1B03] shadow-[0_6px_16px_rgba(224,149,42,0.3)]">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l2.9 6.3 6.9.7-5.1 4.6 1.4 6.8L12 17.3 5.9 20.4l1.4-6.8L2.2 9l6.9-.7z" />
      </svg>
      {points}
    </div>
  );
}
