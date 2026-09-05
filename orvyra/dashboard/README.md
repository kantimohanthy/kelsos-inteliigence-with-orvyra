# ORVYRA Operator Dashboard

The internal dashboard for reviewing pre-call packets and post-call
outcomes. See `source/design-doc.md` in the main ORVYRA repo for the
design direction and Dribbble reference this was built from.

## Run it

```bash
npm install
cp .env.example .env.local   # point ORVYRA_API_URL/KEY at your running ORVYRA instance
npm run dev
```

Requires the ORVYRA API running (see the main `orvyra` repo) — this
app is a pure client of it, no database of its own.

## Screens

- `/` — Prospect queue (every packet, newest first, pursue/no-pursue at a glance)
- `/prospects/[id]` — Packet detail: opportunity hypothesis, conversation
  strategy, company/person context, and call history for one prospect
  (this also serves as the "prospect memory view" from the design doc —
  folded into the detail page rather than a separate screen, since the
  history is really part of understanding one prospect, not its own topic)
- `/outcomes` — Every post-call analysis across all prospects

## Design system

Locked tokens in `app/globals.css` — near-black background, cyan accent
(pursue/positive states only), amber (objections, no-pursue — never
alarm-red, since "don't pursue" is a recommendation, not an error).
Space Grotesk for display, Inter for body, IBM Plex Mono for IDs/
confidence/timestamps. Every confidence score renders as both a number
and a bar; every claim from the API carries its fact/inference tag
inline, never hidden in a tooltip.
