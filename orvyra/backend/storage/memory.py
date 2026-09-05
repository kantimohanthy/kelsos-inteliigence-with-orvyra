"""
Intelligence memory — the "Orvyra Memory" graph.

MVP implementation: in-process dict, keyed by prospect_id, holding
every packet and call analysis ever produced. Swap this module's
internals for Postgres + pgvector when you're ready; nothing outside
this file needs to change, since callers only see get/put.
"""

from __future__ import annotations
from typing import Optional
from .models import IntelligencePacket, CallAnalysis


class IntelligenceMemory:
    def __init__(self) -> None:
        self._packets: dict[str, IntelligencePacket] = {}
        self._history: dict[str, list[CallAnalysis]] = {}

    def save_packet(self, packet: IntelligencePacket) -> None:
        self._packets[packet.prospect_id] = packet

    def get_packet(self, prospect_id: str) -> Optional[IntelligencePacket]:
        return self._packets.get(prospect_id)

    def find_by_identity(self, email: str | None, linkedin_url: str | None) -> Optional[IntelligencePacket]:
        for packet in self._packets.values():
            if email and packet.identity.email == email:
                return packet
            if linkedin_url and packet.identity.linkedin_url == linkedin_url:
                return packet
        return None

    def record_call(self, analysis: CallAnalysis) -> None:
        self._history.setdefault(analysis.prospect_id, []).append(analysis)

    def get_history(self, prospect_id: str) -> list[CallAnalysis]:
        return self._history.get(prospect_id, [])

    def list_packets(self) -> list[IntelligencePacket]:
        packets = list(self._packets.values())
        packets.sort(key=lambda p: p.created_at, reverse=True)
        return packets

    def list_calls(self) -> list[CallAnalysis]:
        all_calls: list[CallAnalysis] = []
        for call_list in self._history.values():
            all_calls.extend(call_list)
        return all_calls

    def clear(self) -> None:
        self._packets.clear()
        self._history.clear()


# Process-wide singleton for the MVP. Replace with a proper
# dependency-injected DB session once you move to Postgres.
memory = IntelligenceMemory()

