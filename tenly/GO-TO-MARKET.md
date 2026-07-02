# Tenly — Go-to-Market Kit

The AI property manager for independent landlords. Wedge: **"Never get a 2am
tenant call again."** Tenly answers tenants, triages maintenance, and dispatches
contractors (with the landlord's approval), 24/7.

**Goal: 3 paying landlords in 2 weeks.** That is the only milestone that matters.

---

## 1. The validation loop (Wizard of Oz)

Do NOT build the AI yet. **Be** the tenant line for the first few landlords —
by hand — and watch whether they (a) trust us with their tenants and (b) pay.

1. Recruit 5–10 small landlords → capture emails on the landing page.
2. For each: get a dedicated number/forwarding set to you; when a tenant texts,
   *you* reply (warm, professional, in the landlord's name), triage, and — with
   the landlord's okay — line up a contractor.
3. Track per landlord: did they hand over the line? did tenants get helped?
   did the landlord stop fielding the routine stuff themselves?
4. To anyone who felt the relief: send the Stripe link. **Card = validated.**

---

## 2. Where the buyers are

Small landlords cluster in obvious places — go where they already complain:

- **BiggerPockets** forums (landlording / property management sub-forums)
- **Reddit:** r/Landlord, r/realestateinvesting, r/PropertyManagement
- **Facebook groups:** local "Landlords of [City]" / REIA groups
- **Local REIA meetups** (real estate investor associations) — in person converts
- **Letting-agent defectors:** landlords who just fired their letting agent

---

## 3. Recruiting post (communities)

> **Independent landlords: I'll be your after-hours tenant line for 2 weeks, free.**
>
> I'm building Tenly — an AI that answers your tenants, sorts the routine
> maintenance stuff, and only pings you when something actually needs you.
>
> Before I build the automation, I want to run it by hand for a few landlords,
> free. For two weeks I'll personally handle your tenant messages (you approve
> anything that costs money). You get your evenings back; I learn what matters.
>
> Got a couple of units and a phone that won't stop buzzing? Comment or DM —
> first 5 landlords.

---

## 4. Cold DM template

> Hey [Name] — saw your post about [tenant headache / being on call]. I'm testing
> Tenly, an AI that handles tenant messages and maintenance triage for landlords.
> Happy to run it for you by hand, free, for two weeks — you approve anything that
> costs money. Worth a quick look?

---

## 5. The tenant-reply playbook (the product, run by hand)

Reply fast, warm, in the landlord's name. Decision tree per message:

- **Routine question** (bin day, how-to) → answer directly, log it.
- **Minor maintenance** (dripping tap, loose handle) → guide a quick fix over
  text; if unresolved, queue a contractor and request landlord approval.
- **Urgent** (no hot water, leak spreading) → fast-track a contractor + notify
  landlord now.
- **Emergency** (flood, gas smell, no heat in winter) → call + text the landlord
  immediately; keep the tenant calm with clear next steps.

Always: confirm back to the tenant, log the request + any photos.

---

## 6. The paid ask (after they feel the relief)

> Glad those quiet evenings landed! I'm turning Tenly into a real product —
> $9 per unit a month, and it runs 24/7 so you're never the after-hours line
> again. Want me to keep it running for your places? [Stripe link]

---

## 7. Pricing

- **$9 / unit / month.** First unit free for 14 days.
- The framing: *"One avoided weekend call-out pays for months of Tenly."*

---

## 8. Go-live checklist

- [ ] Landing page already wired to your Formspree (shared endpoint; create a
      separate Tenly form later if you want clean separation).
- [ ] Create a Stripe Payment Link ($9/unit/mo) → paste into the pricing CTA.
- [ ] Set up a forwarding number tenants can text (Google Voice / a SIM) → you.
- [ ] Turn on GitHub Pages → page live at `/tenly/`.
- [ ] Swap real wins into the "Proof" section as they come in.

---

## 9. Scorecard (decide at day 14)

| Signal | Threshold | Meaning |
|---|---|---|
| Landlords who handed over the line | ≥ 4 of 8 | Trust risk survivable |
| Routine messages resolved without landlord | Most | Core value proven |
| Stripe cards entered | ≥ 3 | Willingness to pay is real |

Yes / yes / yes → build the thin automated version (one number, one triage flow).
Any hard no → pivot the wedge using what you heard from landlords.
