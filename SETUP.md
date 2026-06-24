# Database & retraining setup

This adds a **private database** that collects confirmed results, plus a **retrain
step** you run periodically to update the model every visitor sees.

```
 Visitor's browser ──confirm──▶  Supabase table (private)
        ▲                              │
        │ loads weights.json           │ you read it (service key)
        │                              ▼
   GitHub Pages  ◀──commit──  node retrain.js  ──▶ weights.json
```

The app works **with or without** this. Out of the box (both keys blank) every
confirmation is saved in the visitor's own browser via `localStorage` and survives
refresh — it's just not shared. Configure the steps below to collect submissions
centrally and publish a curated model.

---

## 1. Create a Supabase project (free, no credit card)
1. Sign up at <https://supabase.com> → **New project**. Pick a name + a database
   password (save it). Region: closest to you.
2. Free tier needs no card and **cannot be charged** — if limits are hit it pauses,
   it never bills you.

## 2. Create the table
Dashboard → **SQL Editor** → **New query** → paste all of
[`supabase-schema.sql`](supabase-schema.sql) → **Run**. This creates the
`submissions` table with value-range validation and **insert-only** security
(the browser can add rows but cannot read anyone's data).

## 3. Wire the front end
Dashboard → **Project Settings → API**. Copy:
- **Project URL** (e.g. `https://abcd1234.supabase.co`)
- **anon public** key (the long `eyJ...` — safe to ship in the browser)

Open [`index.html`](index.html), find the config block near the top of the
`<script>`, and paste them in:
```js
const SUPABASE_URL='https://abcd1234.supabase.co';
const SUPABASE_ANON_KEY='eyJhbGciOi...';
```
Now every "I'm diabetic / non-diabetic" confirmation is saved locally **and** sent
to your table. (Verify in Dashboard → **Table Editor → submissions**.)

## 4. Deploy the front end
Push the folder to GitHub and enable **Settings → Pages → Deploy from branch**.
Your dashboard is live at `https://<user>.github.io/<repo>/`. The example CSV and
`weights.json` sit next to it and load automatically.

## 5. Retrain periodically (the "update the weights" step)
When you want to fold collected submissions into the model:
1. Dashboard → **Project Settings → API** → copy the **service_role** key
   (secret — never commit it, never put it in the browser).
2. Run, from the project folder:
   ```bash
   SUPABASE_URL=https://abcd1234.supabase.co \
   SUPABASE_SERVICE_KEY=eyJ...service... \
   node retrain.js
   ```
   It reads the base cohort + all submissions, **drops out-of-range rows**, trains,
   and writes [`weights.json`](weights.json).
3. Review the printed summary, then **commit `weights.json`**. Every visitor now
   loads the updated curated model on next visit (status shows "curated model").

No live database? `node retrain.js` alone retrains on just the base CSV, and
`node retrain.js submissions.csv` uses a local CSV export.

---

## Notes
- **This manual retrain is your safety gate.** Bad/spam rows sit harmlessly in the
  table until *you* choose to retrain, and out-of-range values are dropped both at
  the database (schema constraints) and in `retrain.js`. If you ever automate
  retraining, add automated trust filters to replace this human review.
- **Privacy.** Only the blood-work numbers + the 0/1 outcome are stored — no name,
  email, or identifier. The consent line on the confirm button reflects this. You
  are nonetheless the custodian of this data; keep it anonymous.
- **Rate limiting** (optional). Supabase has no per-IP limit natively. If abuse
  becomes real, front the insert with a Supabase Edge Function or put Cloudflare
  Turnstile on the confirm action. For an unadvertised project this is rarely
  needed — the insert-only policy + validation + manual retrain already contain it.
- **Keys.** The `anon` key is public by design (insert-only). The `service_role`
  key is all-powerful — keep it in your shell/CI secrets only.
