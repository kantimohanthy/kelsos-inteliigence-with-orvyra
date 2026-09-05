from __future__ import annotations
from storage.models import PostCallInput, CallAnalysis
from storage.memory import memory
from intelligence.reasoning import analyze_call


def run_post_call(payload: PostCallInput) -> CallAnalysis:
    analysis = analyze_call(payload)
    memory.record_call(analysis)
    return analysis
