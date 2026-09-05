import Link from "next/link";
import { notFound } from "next/navigation";
import { orvyra } from "@/lib/orvyra";
import { Card, PursuePill, ConfidenceBar, ClaimTag, Mono, OutcomePill } from "@/components/ui";

export default async function ProspectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let packet;
  try {
    packet = await orvyra.getProspect(id);
  } catch {
    notFound();
  }

  let history: Awaited<ReturnType<typeof orvyra.getProspectHistory>> = [];
  try {
    history = await orvyra.getProspectHistory(id);
  } catch {
    // history is supplementary — a failure here shouldn't blank the whole page
  }

  const { opportunity, conversation_strategy, company_context, person_context, identity } = packet;

  return (
    <div className="max-w-3xl px-4 sm:px-8 py-10">
      <Link href="/" className="text-sm text-text-muted hover:text-text">
        ← Queue
      </Link>

      <header className="mt-4 mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold">
            {identity.name}
          </h1>
          <p className="text-text-muted text-sm mt-1">
            {identity.company ?? "No company on file"}
            {person_context.role && ` · ${person_context.role}`}
          </p>
          <Mono className="text-xs text-text-muted mt-1 block">{packet.prospect_id}</Mono>
        </div>
        <PursuePill pursue={opportunity.pursue} />
      </header>

      {/* Opportunity */}
      <Card className="p-5 mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium text-sm text-text-muted">Opportunity hypothesis</h2>
          <ConfidenceBar value={opportunity.confidence} />
        </div>

        {opportunity.pursue ? (
          <>
            <p className="text-text">{opportunity.primary_problem}</p>
            {opportunity.value_hypothesis && (
              <p className="text-text-muted text-sm mt-2">{opportunity.value_hypothesis}</p>
            )}
            {opportunity.likely_objections.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-text-muted mb-1.5">Likely objections</p>
                <ul className="flex flex-wrap gap-1.5">
                  {opportunity.likely_objections.map((o) => (
                    <li
                      key={o}
                      className="text-xs px-2 py-1 rounded border border-hairline text-text-muted"
                    >
                      {o}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {opportunity.recommended_angle && (
              <p className="text-sm text-cyan mt-4">→ {opportunity.recommended_angle}</p>
            )}
          </>
        ) : (
          <p className="text-amber text-sm">{opportunity.reason_if_not_pursue}</p>
        )}
      </Card>

      {/* Conversation strategy — explicitly not a script */}
      {conversation_strategy && (
        <Card className="p-5 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium text-sm text-text-muted">Conversation strategy</h2>
            <span className="text-[10px] uppercase tracking-wide text-text-muted border border-hairline rounded px-1.5 py-0.5">
              not a script
            </span>
          </div>
          {conversation_strategy.opening_angle && (
            <p className="text-sm text-text mb-4">{conversation_strategy.opening_angle}</p>
          )}
          {conversation_strategy.discovery_questions.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-text-muted mb-1.5">Discovery questions</p>
              <ul className="flex flex-col gap-1.5">
                {conversation_strategy.discovery_questions.map((q) => (
                  <li key={q} className="text-sm text-text pl-3 border-l border-hairline">
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {conversation_strategy.avoid.length > 0 && (
            <div>
              <p className="text-xs text-text-muted mb-1.5">Avoid</p>
              <ul className="flex flex-wrap gap-1.5">
                {conversation_strategy.avoid.map((a) => (
                  <li
                    key={a}
                    className="text-xs px-2 py-1 rounded border border-amber/30 text-amber"
                  >
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Company + person context */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <Card className="p-5">
          <h2 className="font-medium text-sm text-text-muted mb-3">Company</h2>
          <p className="text-sm text-text">{company_context.industry ?? "Industry unknown"}</p>
          <ul className="mt-3 flex flex-col gap-1.5">
            {company_context.recent_signals.map((s) => (
              <li key={s} className="text-xs text-text-muted flex items-start gap-1.5">
                <span className="mt-1 w-1 h-1 rounded-full bg-text-muted shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-5">
          <h2 className="font-medium text-sm text-text-muted mb-3">Person</h2>
          <p className="text-sm text-text">
            {person_context.role ?? "Role unknown"}
            {person_context.seniority && ` · ${person_context.seniority}`}
          </p>
          {person_context.probable_priorities.length > 0 && (
            <ul className="mt-3 flex flex-col gap-2">
              {person_context.probable_priorities.map((c) => (
                <li key={c.claim} className="flex items-start gap-2">
                  <ClaimTag type={c.type} />
                  <span className="text-xs text-text-muted">{c.claim}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Memory — prior interactions for this prospect */}
      <Card className="p-5">
        <h2 className="font-medium text-sm text-text-muted mb-3">Call history</h2>
        {history.length === 0 ? (
          <p className="text-xs text-text-muted">No calls yet for this prospect.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {history.map((h) => (
              <li
                key={h.conversation_id}
                className="flex items-center justify-between border-t border-hairline pt-3 first:border-t-0 first:pt-0"
              >
                <div className="flex items-center gap-3">
                  <Mono className="text-xs text-text-muted">{h.conversation_id}</Mono>
                  <OutcomePill outcome={h.outcome} />
                </div>
                <ConfidenceBar value={h.intent_score} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
