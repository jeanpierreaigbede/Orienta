import { LEVEL_BADGE, ORIENTATION_LABELS, STATUS_BADGE, STATUS_LABELS } from "@/lib/texts";

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <span className={`badge ${STATUS_BADGE[status] ?? ""}`}>{label ?? STATUS_LABELS[status] ?? status}</span>;
}

export function LevelBadge({ level }: { level: string | null }) {
  if (!level) return <span className="muted">—</span>;
  return <span className={`badge ${LEVEL_BADGE[level]}`}>{ORIENTATION_LABELS[level]}</span>;
}
