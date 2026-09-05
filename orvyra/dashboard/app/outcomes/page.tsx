import Link from "next/link";
import { orvyra } from "@/lib/orvyra";
import { Card, OutcomePill, ConfidenceBar, Mono, EmptyState } from "@/components/ui";

export default async function OutcomesPage() {
  let calls: Awaited<ReturnType<typeof orvyra.listCalls>> = [];
  let error: string | null = null;

  try {
    calls = await orvyra.listCalls();
  } catch {
    error = "Couldn't reach ORVYRA. Is the API running?";
  }

  return (
    <div className="max-w-4xl px-4 sm:px-8 py-10">
      <header className="mb-8">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold">
          Call outcomes
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Every post-call analysis, as it lands.
        </p>
      </header>

      {error && (
        <Card className="p-4 mb-6 border-amber/30">
          <p className="text-sm text-amber">{error}</p>
        </Card>
      )}

      {!error && calls.length === 0 && (
        <EmptyState
          title="No calls yet"
          body="When Klesos sends a transcript to the post-call endpoint, results will show up here."
        />
      )}

      <div className="flex flex-col gap-2">
        {calls.map((c) => (
          <Link key={c.conversation_id} href={`/prospects/${c.prospect_id}`}>
            <Card className="p-4 hover:border-cyan/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Mono className="text-xs text-text-muted">{c.conversation_id}</Mono>
                  <OutcomePill outcome={c.outcome} />
                </div>
                <p className="text-xs text-text-muted mt-2">
                  Next: {c.next_best_action.action.replaceAll("_", " ")}
                  {c.next_best_action.channel && ` via ${c.next_best_action.channel}`}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-text-muted mb-1">Intent</p>
                <ConfidenceBar value={c.intent_score} />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
