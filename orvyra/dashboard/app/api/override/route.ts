import { NextResponse } from "next/server";
import { orvyra } from "@/lib/orvyra";

export async function PATCH(req: Request) {
  try {
    const { prospect_id, pursue, reason } = await req.json();
    if (!prospect_id || typeof pursue !== "boolean" || !reason) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }
    const result = await orvyra.overrideDecision(prospect_id, pursue, reason);
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Override failed" }, { status: 500 });
  }
}
