interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

/** État d'erreur partagé — même gabarit sur tous les écrans. */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-16 text-center">
      <p className="text-sm text-danger">{message}</p>
      <button onClick={onRetry} className="rounded-2xl border border-line px-5 py-2.5 text-sm font-bold text-ink-body">
        Réessayer
      </button>
    </div>
  );
}
