import Link from "next/link";
import { orvyra } from "@/lib/orvyra";
import { Card, PursuePill, ConfidenceBar, Mono, EmptyState } from "@/components/ui";

export default async function QueuePage() {
  let prospects: Awaited<ReturnType<typeof orvyra.listProspects>> = [];
  let error: string | null = null;

  try {
    prospects = await orvyra.listProspects();
  } catch {
    error = "Couldn't reach ORVYRA. Is the API running?";
  }

  return (
    <div className="max-w-4xl px-4 sm:px-8 py-10">
      <header className="mb-8">
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold">
          Prospect queue
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Every packet ORVYRA has built, newest first.
        </p>
      </header>

      {error && (
        <Card className="p-4 mb-6 border-amber/30">
          <p className="text-sm text-amber">{error}</p>
        </Card>
      )}

      {!error && prospects.length === 0 && (
        <EmptyState
          title="No prospects yet"
          body="When Klesos calls the pre-call endpoint, packets will show up here."
        />
      )}

      <div className="flex flex-col gap-2">
        {prospects.map((p) => (
          <Link key={p.prospect_id} href={`/prospects/${p.prospect_id}`}>
            <Card className="p-4 hover:border-cyan/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium truncate">{p.identity.name}</p>
                  {p.identity.company && (
                    <span className="text-text-muted text-sm truncate">
                      · {p.identity.company}
                    </span>
                  )}
                </div>
                <Mono className="text-xs text-text-muted mt-1 block">
                  {p.prospect_id}
                </Mono>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <ConfidenceBar value={p.opportunity.confidence} />
                <PursuePill pursue={p.opportunity.pursue} />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
