# PaidUp — Go-to-Market Kit

Everything needed to drive the first 10 users to the landing page and validate
willingness to pay. **Goal: 3 real Stripe cards in 2 weeks.** That is the only
milestone that matters right now.

---

## 1. The validation loop (what we're actually doing)

We do NOT build the AI yet. We **be** the AI ("Wizard of Oz") for the first 10
users — chasing their late invoices by hand — and watch whether they (a) trust
us with it and (b) pay to keep it running.

1. Drive 10 freelancers to the landing page → capture emails.
2. For each: they forward an overdue invoice; we draft the follow-up sequence
   in their voice; they approve; we send.
3. Track per user: did they approve? did they edit heavily? did it get paid?
4. To anyone we get paid: send the Stripe link. **Card = validated.**

---

## 2. Recruiting post (communities)

Post in r/freelance, r/consulting, r/smallbusiness, IndieHackers, and 2–3 niche
Slack/Discord groups. Adjust tone per community. Lead with giving, not selling.

> **Got clients who pay late? I'll get one invoice paid for you — free.**
>
> I'm building a tool that automatically chases late-paying clients so
> freelancers don't have to do the awkward follow-up dance.
>
> Before I build it, I want to do it manually for a few of you — free.
>
> If you've got an overdue invoice right now, I'll write and run the follow-up
> sequence for you (you approve every message before it sends). You keep 100% of
> whatever comes in. I just want to learn what works.
>
> 15-min call to set it up. First 10 people — comment or DM.

---

## 3. Cold DM template (if community posts are slow)

Find freelancers posting about cash flow / late clients on X/LinkedIn. Keep it
short, specific, and free.

> Hey [Name] — saw your post about [late client / cash flow]. I'm testing a tool
> that chases late invoices for freelancers. Happy to do it for you by hand,
> free, on one overdue invoice — you approve every message, you keep everything
> that comes in. Worth a quick look?

---

## 4. The follow-up sequence (the product, run by hand)

Assumes Net-30. Send in the client's voice. You approve before each send.

**Touch 1 — Day +3 past due (warm nudge)**
> Hi [Name] — hope you're well! Just flagging that invoice #[X] for $[amount] was
> due [date]. Totally understand things slip through — could you let me know
> roughly when I can expect it? Happy to resend if it's easier. Thanks!

**Touch 2 — Day +10 (firm + remove friction)**
> Hi [Name], following up on invoice #[X] ($[amount]), now [N] days past due. To
> make it simple, here's the payment link again: [link]. If there's a holdup on
> your end, just let me know and we'll sort it. Appreciate you getting this
> wrapped up this week.

**Touch 3 — Day +18 (consequence, still professional)**
> Hi [Name], invoice #[X] ($[amount]) is now [N] days overdue. I'll need to pause
> any further work and apply the [late fee / interest per our agreement] starting
> [date]. I'd much rather not — can we get this settled by [date]? Send payment
> here: [link].

---

## 5. The paid ask (after a win)

To any user whose invoice got paid:

> Glad that one landed! I'm turning this into a tool — $29/mo plus 1% of whatever
> it recovers, and it runs automatically so you never chase again. Want me to keep
> it running for your account? [Stripe link]

---

## 6. Pricing

- **$29/mo + 1% of recovered invoices.** Aligned: we win when you get paid.
- The ROI line: *"$8,000 in late invoices? PaidUp costs $29."*

---

## 7. Go-live checklist (make the page collect money)

- [ ] Set the signup form `action=` to a Formspree/Tally/Mailchimp endpoint.
- [ ] Set the pricing CTA `href=` to a Stripe Payment Link.
- [ ] Turn on GitHub Pages → page live at `/paidup/`.
- [ ] Swap real win screenshots into the "Proof" section as they come in.

---

## 8. Scorecard (decide at day 14)

| Signal | Threshold | Meaning |
|---|---|---|
| Forwarded invoices + let us send | ≥ 5 of 10 | Trust risk survivable |
| Drafts sent near-as-is | Most | Voice/quality is tractable |
| Stripe cards entered | ≥ 3 | Willingness to pay is real |

Yes / yes / yes → build the thin automated version of exactly this workflow.
Any hard no → pivot the wedge using what you heard on the calls.
