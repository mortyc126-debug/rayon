-- ═══════════════════════════════════════
-- РАЙОН v8 — Supabase Schema
-- Запусти в Supabase → SQL Editor
-- ═══════════════════════════════════════

-- Players
create table if not exists players (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  faction text not null check (faction in ('bandits','cops')),
  gold int not null default 1200,
  troops int not null default 180,
  xp int not null default 0,
  level int not null default 1,
  hq_level int not null default 1,
  commander text,
  special_cooldown int not null default 0,
  stats jsonb not null default '{"spy":0,"reinforce":0,"capture":0,"siege":0,"oblava":0}',
  last_active timestamptz not null default now(),
  created_at timestamptz not null default now()
);

-- Blocks (105 total: 7 districts × ~15 blocks)
-- Seeded by first client that loads the game
create table if not exists blocks (
  id text primary key,          -- "distId_blockIdx" e.g. "0_3"
  district_id int not null,
  block_idx int not null,
  base_income int not null default 5,
  faction text not null default 'neutral', -- 'neutral','e1','e2','e3','player'
  owner_id uuid references players(id) on delete set null,
  defense int not null default 20,
  level int not null default 1,
  income int not null default 0,
  siege_ends_at timestamptz,
  siege_duration int,
  siege_attacker_id uuid references players(id) on delete set null,
  siege_attacker_faction text,     -- 'e1'/'e2'/'e3' for AI
  siege_troops int,
  nayezd_until timestamptz,
  updated_at timestamptz not null default now()
);

-- Game events feed (shared, last 50)
create table if not exists game_events (
  id bigserial primary key,
  type text not null,             -- 'ev-cap','ev-atk','ev-def','ev-inf','ev-event'
  message text not null,
  player_name text,
  player_faction text,
  created_at timestamptz not null default now()
);

-- Global state (one row, id=1)
create table if not exists global_state (
  id int primary key default 1,
  next_event_at timestamptz not null default (now() + interval '5 minutes'),
  next_event_type text not null default '⚡ Горячая точка',
  active_event text,
  active_event_ends_at timestamptz,
  hot_block_id text,
  special_reset_at timestamptz not null default (now() + interval '4 hours')
);
insert into global_state (id) values (1) on conflict (id) do nothing;

-- Indexes
create index if not exists blocks_district_id_idx on blocks(district_id);
create index if not exists blocks_owner_id_idx on blocks(owner_id);
create index if not exists game_events_created_at_idx on game_events(created_at desc);

-- RLS (permissive for game MVP)
alter table players enable row level security;
alter table blocks enable row level security;
alter table game_events enable row level security;
alter table global_state enable row level security;

drop policy if exists "allow_all_players" on players;
drop policy if exists "allow_all_blocks" on blocks;
drop policy if exists "allow_all_events" on game_events;
drop policy if exists "allow_all_global" on global_state;

create policy "allow_all_players" on players for all using (true) with check (true);
create policy "allow_all_blocks" on blocks for all using (true) with check (true);
create policy "allow_all_events" on game_events for all using (true) with check (true);
create policy "allow_all_global" on global_state for all using (true) with check (true);

-- Enable Realtime for these tables
-- (также включи в Supabase → Table Editor → Realtime)
alter publication supabase_realtime add table blocks;
alter publication supabase_realtime add table game_events;
alter publication supabase_realtime add table global_state;
alter publication supabase_realtime add table players;

-- Auto-cleanup old events (keep last 100)
create or replace function cleanup_events() returns trigger language plpgsql as $$
begin
  delete from game_events where id in (
    select id from game_events order by created_at desc offset 100
  );
  return new;
end;
$$;
drop trigger if exists trg_cleanup_events on game_events;
create trigger trg_cleanup_events after insert on game_events
  for each row execute function cleanup_events();
