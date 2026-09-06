"use client";

import { useState } from "react";
import { Mono } from "./ui";

export function OverrideControl({
  prospectId,
  currentPursue,
  existingOverride,
}: {
  prospectId: string;
  currentPursue: boolean;
  existingOverride?: { pursue: boolean; reason: string; created_at: string | null } | null;
}) {
  const [overrideState, setOverrideState] = useState<{
    pursue: boolean;
    reason: string;
    created_at: string | null;
  } | null>(existingOverride ?? null);
  const [isOpen, setIsOpen] = useState(false);
  const [targetPursue, setTargetPursue] = useState(!currentPursue);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activePursue = overrideState ? overrideState.pursue : currentPursue;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Please provide a reason for the decision override.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/override`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prospect_id: prospectId, pursue: targetPursue, reason }),
      });
      if (!res.ok) {
        throw new Error(`Failed to save override (${res.status})`);
      }
      const data = await res.json();
      setOverrideState({
        pursue: data.pursue,
        reason: data.reason,
        created_at: data.created_at,
      });
      setIsOpen(false);
      setReason("");
    } catch (err: any) {
      setError(err.message || "Failed to submit override");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-4 pt-4 border-t border-hairline">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs text-text-muted">Operator Decision Override: </span>
          {overrideState ? (
            <span
              className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded font-medium ${
                overrideState.pursue
                  ? "bg-cyan/20 text-cyan border border-cyan/40"
                  : "bg-amber/20 text-amber border border-amber/40"
              }`}
            >
              Overridden to: {overrideState.pursue ? "PURSUE" : "DO NOT PURSUE"}
            </span>
          ) : (
            <span className="text-xs text-text-muted italic">No operator override active</span>
          )}
        </div>
        <button
          onClick={() => {
            setTargetPursue(!activePursue);
            setIsOpen(!isOpen);
          }}
          className="text-xs px-2.5 py-1 rounded bg-surface border border-hairline hover:border-cyan text-text hover:text-cyan transition-colors"
        >
          {isOpen ? "Cancel Override" : "Override Decision"}
        </button>
      </div>

      {overrideState && (
        <div className="mt-2 text-xs bg-surface/50 p-2.5 rounded border border-hairline">
          <p className="text-text font-medium">Override Reason: {overrideState.reason}</p>
          {overrideState.created_at && (
            <Mono className="text-[10px] text-text-muted mt-1 block">
              Recorded at: {new Date(overrideState.created_at).toLocaleString()}
            </Mono>
          )}
        </div>
      )}

      {isOpen && (
        <form onSubmit={handleSubmit} className="mt-3 p-3 bg-surface border border-cyan/30 rounded-lg text-xs">
          <p className="font-medium text-text mb-2">
            Set Manual Override Decision to:{" "}
            <span className={targetPursue ? "text-cyan" : "text-amber"}>
              {targetPursue ? "PURSUE" : "DO NOT PURSUE"}
            </span>
          </p>

          <label className="block text-text-muted mb-1">Reason for override (required):</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Spoke to CEO directly; customer confirmed interest"
            className="w-full bg-background border border-hairline rounded px-2.5 py-1.5 text-text focus:outline-none focus:border-cyan mb-2"
          />

          {error && <p className="text-amber text-xs mb-2">{error}</p>}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="px-2.5 py-1 rounded border border-hairline text-text-muted hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1 rounded bg-cyan text-background font-medium hover:bg-cyan/90 disabled:opacity-50"
            >
              {loading ? "Saving..." : "Save Override"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
