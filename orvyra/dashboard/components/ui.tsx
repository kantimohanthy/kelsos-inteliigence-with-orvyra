export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-surface border border-hairline rounded-lg ${className}`}>
      {children}
    </div>
  );
}

export function Mono({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`font-[family-name:var(--font-mono)] ${className}`}>{children}</span>;
}

/**
 * Pursue / no-pursue is a first-class recommendation, not an error state —
 * per the design doc, never render "don't pursue" as greyed-out or apologetic.
 */
export function PursuePill({ pursue }: { pursue: boolean }) {
  if (pursue) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-cyan/10 text-cyan border border-cyan/30">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan" />
        Recommended: pursue
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-amber/10 text-amber border border-amber/30">
      <span className="w-1.5 h-1.5 rounded-full bg-amber" />
      Recommended: don't pursue
    </span>
  );
}

const OUTCOME_STYLES: Record<string, string> = {
  interested_follow_up: "bg-cyan/10 text-cyan border-cyan/30",
  booked_meeting: "bg-cyan/10 text-cyan border-cyan/30",
  not_interested: "bg-amber/10 text-amber border-amber/30",
  needs_more_info: "bg-text-muted/10 text-text-muted border-hairline",
};

export function OutcomePill({ outcome }: { outcome: string }) {
  const style = OUTCOME_STYLES[outcome] ?? OUTCOME_STYLES.needs_more_info;
  return (
    <span className={`inline-flex px-2.5 py-1 rounded-full text-xs border ${style}`}>
      {outcome.replaceAll("_", " ")}
    </span>
  );
}

/** Confidence renders as a number + bar in mono — never just a bare percentage. */
export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-hairline overflow-hidden">
        <div className="h-full bg-cyan" style={{ width: `${pct}%` }} />
      </div>
      <Mono className="text-xs text-text-muted">{pct}%</Mono>
    </div>
  );
}

/** Every claim in the UI carries its fact/inference tag — never hidden in a tooltip. */
export function ClaimTag({ type }: { type: "fact" | "inference" }) {
  return (
    <span
      className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded border ${
        type === "fact"
          ? "text-text-muted border-hairline"
          : "text-amber border-amber/30"
      }`}
    >
      {type}
    </span>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-dashed border-hairline rounded-lg py-16 text-center">
      <p className="font-[family-name:var(--font-display)] text-text">{title}</p>
      <p className="text-sm text-text-muted mt-1 max-w-sm mx-auto">{body}</p>
    </div>
  );
}
