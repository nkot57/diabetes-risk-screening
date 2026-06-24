-- =====================================================================
-- DiabetesNet — private submissions table
-- Run this once in Supabase: Dashboard → SQL Editor → New query → Run.
-- =====================================================================

-- Anonymous blood-work submissions. No names, no identifiers — values only.
create table if not exists public.submissions (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  age   numeric, bmi numeric, chol numeric, tg numeric,
  hdl   numeric, ldl numeric, cr   numeric, bun numeric,
  diagnosis smallint not null,

  -- ---- front-line validation: reject impossible values at the database ----
  constraint dx_binary check (diagnosis in (0,1)),
  constraint age_ok  check (age  is null or age  between 0 and 120),
  constraint bmi_ok  check (bmi  is null or bmi  between 8 and 90),
  constraint chol_ok check (chol is null or chol between 0 and 20),
  constraint tg_ok   check (tg   is null or tg   between 0 and 30),
  constraint hdl_ok  check (hdl  is null or hdl  between 0 and 10),
  constraint ldl_ok  check (ldl  is null or ldl  between 0 and 20),
  constraint cr_ok   check (cr   is null or cr   between 5 and 2000),
  constraint bun_ok  check (bun  is null or bun  between 0 and 100)
);

-- =====================================================================
-- Row Level Security: the browser (anon key) may INSERT only.
-- It can add a row but CANNOT read, update, or delete anyone's data.
-- You read everything from retrain.js using the service_role key,
-- which bypasses RLS.
-- =====================================================================
alter table public.submissions enable row level security;

drop policy if exists "anon can insert" on public.submissions;
create policy "anon can insert"
  on public.submissions
  for insert
  to anon
  with check (true);

-- No SELECT / UPDATE / DELETE policy for anon  =>  all denied by default.

-- Table privileges the anon role needs to perform the insert.
grant usage on schema public to anon;
grant insert on table public.submissions to anon;

-- =====================================================================
-- Optional: keep a single row per identical submission to blunt naive
-- flooding (does not stop a determined attacker — your manual retrain
-- review is the real backstop). Uncomment to enable.
-- =====================================================================
-- create unique index if not exists submissions_dedup
--   on public.submissions (age,bmi,chol,tg,hdl,ldl,cr,bun,diagnosis);
