import Link from "next/link";
import { notFound } from "next/navigation";
import { orvyra } from "@/lib/orvyra";
import { Card, PursuePill, ConfidenceBar, ClaimTag, Mono, OutcomePill } from "@/components/ui";
import { OverrideControl } from "@/components/override-control";

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

  let existingOverride = null;
  try {
    existingOverride = await orvyra.getOverride(id);
  } catch {
    // override data is supplementary
  }

  const { opportunity, conversation_strategy, company_context, person_context, identity, facts, sources, warnings, status } = packet;

  const isNeedsReview = status === "needs_review" || warnings.some((w) => w.toLowerCase().includes("identity conflict"));
  const isFailed = status === "failed" || warnings.some((w) => w.toLowerCase().includes("issue") || w.toLowerCase().includes("error"));

  return (
    <div className="max-w-3xl px-4 sm:px-8 py-10">
      <Link href="/" className="text-sm text-text-muted hover:text-text">
        ← Queue
      </Link>

      {/* Explicit State Banners */}
      {isNeedsReview && (
        <div className="mt-4 p-4 rounded-lg bg-amber/10 border border-amber/30 text-amber text-sm">
          <div className="flex items-center gap-2 font-medium">
            <span className="w-2 h-2 rounded-full bg-amber shrink-0" />
            Needs Operator Review — Identity Conflict Detected
          </div>
          <p className="mt-1 text-xs text-amber/90">
            Multiple conflicting identity signals were found during lead enrichment. Please verify company & prospect details before initiating outbound dials.
          </p>
        </div>
      )}

      {isFailed && !isNeedsReview && (
        <div className="mt-4 p-4 rounded-lg bg-amber/10 border border-amber/30 text-amber text-sm">
          <div className="flex items-center gap-2 font-medium">
            <span className="w-2 h-2 rounded-full bg-amber shrink-0" />
            Enrichment Issue / Partial Scrape
          </div>
          <p className="mt-1 text-xs text-amber/90">
            One or more crawl/enrichment requests failed or hit page access limits during packet generation.
          </p>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-surface border border-hairline text-xs text-text-muted">
          <p className="font-medium text-text mb-1">Ingestion Notices & Warnings:</p>
          <ul className="list-disc list-inside space-y-0.5">
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

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

        {/* Operator Decision Override Control */}
        <OverrideControl
          prospectId={packet.prospect_id}
          currentPursue={opportunity.pursue}
          existingOverride={existingOverride}
        />
      </Card>

      {/* Evidence & Atomic Claims Display */}
      <Card className="p-5 mb-4">
        <h2 className="font-medium text-sm text-text-muted mb-3">Extracted Claims & Supporting Evidence</h2>
        {facts.length === 0 ? (
          <p className="text-xs text-text-muted">No explicit claims extracted for this prospect.</p>
        ) : (
          <div className="space-y-4">
            {facts.map((claimItem, idx) => (
              <div key={idx} className="p-3 bg-background/50 border border-hairline rounded-lg text-xs">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <ClaimTag type={claimItem.type} />
                    <span className="font-medium text-text">{claimItem.claim}</span>
                  </div>
                  <Mono className="text-[10px] text-text-muted">{Math.round(claimItem.confidence * 100)}% conf</Mono>
                </div>

                {/* Evidence provenance list */}
                {claimItem.evidence && claimItem.evidence.length > 0 ? (
                  <div className="mt-2 pl-3 border-l border-cyan/30 space-y-1">
                    {claimItem.evidence.map((ev, evIdx) => (
                      <div key={evIdx} className="text-[11px] text-text-muted">
                        {ev.excerpt && <p className="italic text-text/80">"{ev.excerpt}"</p>}
                        <div className="flex items-center gap-2 mt-0.5 text-[10px]">
                          <span className="uppercase text-cyan">{ev.source_type}</span>
                          {ev.url && (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyan underline truncate max-w-xs"
                            >
                              {ev.url}
                            </a>
                          )}
                          {ev.retrieval_time && (
                            <Mono className="text-text-muted">
                              {new Date(ev.retrieval_time).toLocaleDateString()}
                            </Mono>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[10px] text-text-muted italic mt-1">Derived from general prospect input context</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Global Evidence Sources Summary */}
        {sources && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-hairline">
            <p className="text-xs text-text-muted font-medium mb-1.5">Document Sources ({sources.length}):</p>
            <div className="flex flex-wrap gap-2">
              {sources.map((src, sIdx) => (
                <div key={sIdx} className="text-[10px] p-2 bg-surface border border-hairline rounded max-w-full">
                  <span className="font-medium text-text">{src.source_type}</span>
                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className="block text-cyan underline truncate max-w-xs mt-0.5"
                    >
                      {src.url}
                    </a>
                  )}
                  {src.excerpt && <p className="text-text-muted truncate max-w-xs mt-0.5">{src.excerpt}</p>}
                </div>
              ))}
            </div>
          </div>
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
