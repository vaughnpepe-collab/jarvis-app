# Leads — HW Web Design sales pipeline

Real prospects for the web-design business, generated from live data. This is
the **top of the funnel**: find local businesses with weak or missing websites,
rank by how easy they are to sell, and hand you ready-to-use outreach.

## Files

| File | What it is |
|------|------------|
| `leads_high_wycombe_area.md` | **The call sheet.** Worst sites first, bucketed by how actionable each lead is. Start here. |
| `outreach_pack_high_wycombe_area.md` | **Ready-to-send** call openers + personalised emails for the top callable leads. |
| `leads_high_wycombe_area.csv` | Every business found, with full flaw detail — open in Excel/Sheets to sort & filter. |

## How to work it

1. Open the call sheet. Work the 🟢 **No website + phone** list first — easiest sale.
2. Then 🟡 **Has a site, real flaws** — the flaws are read from the live page, so
   you can quote them on the call with confidence.
3. Grab the matching script in `outreach_pack_*.md`, swap in your real phone
   number and name, and go.
4. Log every call (business, outcome, follow-up date) — see `../outreach/phone_script.md`.

Rule of thumb from the phone script: ~1 in 10 calls becomes a conversation,
~1 in 5 of those converts. 20 calls/day → a couple of live deals a week.

## Refresh / expand

```bash
# Re-run the default area sweep (High Wycombe, Marlow, Beaconsfield, Amersham)
python area_sweep.py

# Target different towns or niches
python area_sweep.py --towns "Reading, UK;Slough, UK" --niches "dentist;gym;restaurant"
```

### Get 5–10× more leads (recommended)
The free OpenStreetMap source misses many businesses and most phone numbers.
A **Google Places API key** dramatically improves coverage and contact details:

```bash
export GOOGLE_PLACES_KEY=your_key_here
python area_sweep.py
```

The prospector auto-detects the key and switches source automatically.
