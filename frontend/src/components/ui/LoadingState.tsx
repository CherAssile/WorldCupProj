interface LoadingStateProps {
  message: string;
}

/** État de chargement partagé — même gabarit sur tous les écrans. */
export function LoadingState({ message }: LoadingStateProps) {
  return (
    <div className="flex flex-1 items-center justify-center px-5 py-16 text-sm text-ink-secondary">{message}</div>
  );
}
