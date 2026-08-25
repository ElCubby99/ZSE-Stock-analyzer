// NALOG M30: ljudski komentar u raspravi — SVI limiti i filter na serveru.
// Deploy: supabase functions deploy discussion-comment --no-verify-jwt
// Secrets: COMMENT_IP_SALT (nasumičan string; ip_hash = sha256(ip+salt)).
// Env flag: SUMMONS_ENABLED — M77: default ON (red @spomena se puni, a
// obrađuje ga dnevni pipeline: src/forum_events.py, samo ODOBRENI komentari).
// Postavi secret SUMMONS_ENABLED=false za privremeno gašenje bez redeploya.
//
// Sigurnosni model kao delete-account: identitet ISKLJUČIVO iz JWT-a
// pozivatelja; service role samo unutar functiona. Izravni INSERT u
// discussion_posts NE postoji (RLS bez policyja) — ovo je jedina vrata.
//
// Faza 1 (bez API klasifikatora): SVAKI komentar ide u 'pending' za admin
// review; regex filter sumnjive odmah označi 'flagged'. Struktura je ista,
// klasifikator (Haiku) se kasnije samo umetne na mjesto filtera.
import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set([
  "https://www.burzovnilist.com",
  "https://burzovnilist.com",
  "http://localhost:5173",
  "http://localhost:4173",
]);
const corsFor = (req: Request) => {
  const o = req.headers.get("origin");
  return {
    "Access-Control-Allow-Origin":
      o && ALLOWED_ORIGINS.has(o) ? o : "https://www.burzovnilist.com",
    "Vary": "Origin",
    "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
};

// filter faze 1: spam / uvrede / prompt-injection / "preporuke" -> flagged
const SUSPECT = [
  /https?:\/\/(?!www\.burzovnilist\.com)/i,          // vanjski linkovi = spam signal
  /\b(ignore|zanemari).{0,30}(instructions|upute)\b/i, // prompt injection
  /\bsystem prompt\b/i,
  /\b(kupite|prodajte|kupi|prodaj)\b.{0,40}\bdionic/i, // "preporuka"
  /\bzajam[čc]en[ai]? (prinos|zarada)\b/i,
];

async function sha256hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  const CORS = corsFor(req);
  const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body),
      { status, headers: { ...CORS, "Content-Type": "application/json" } });
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "POST only" });

  // 1) identitet iz JWT-a pozivatelja
  const url = Deno.env.get("SUPABASE_URL")!;
  const authHeader = req.headers.get("Authorization") ?? "";
  const caller = createClient(url, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: authHeader } },
  });
  const { data: { user }, error: uErr } = await caller.auth.getUser();
  if (uErr || !user) return json(401, { error: "prijava je obavezna" });
  if (!user.email_confirmed_at) {
    return json(403, { error: "email nije potvrđen" });
  }

  let p: Record<string, unknown>;
  try { p = await req.json(); } catch { return json(400, { error: "nevaljan JSON" }); }
  const discussion_id = String(p.discussion_id ?? "");
  const body = String(p.body ?? "").trim();
  const reply_to = p.reply_to == null ? null : String(p.reply_to);
  if (!/^[0-9a-f-]{36}$/.test(discussion_id)) return json(400, { error: "discussion_id" });
  if (!body) return json(400, { error: "prazan komentar" });

  const admin = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  // 2) limiti iz usage_limits (config u bazi, editabilno u /admin)
  const { data: limRows } = await admin.from("usage_limits").select("key,value_int");
  const lim = Object.fromEntries((limRows ?? []).map((r) => [r.key, r.value_int]));
  const maxChars = lim.comment_max_chars ?? 2000;
  if (body.length > maxChars) {
    return json(400, { error: `komentar duži od ${maxChars} znakova` });
  }

  // 3) starost računa + flagovi
  const cooldownH = lim.new_account_cooldown_hours ?? 48;
  const ageMs = Date.now() - Date.parse(user.created_at);
  if (ageMs < cooldownH * 3600_000) {
    return json(403, { error: `račun mora biti stariji od ${cooldownH} h` });
  }
  const { data: flags } = await admin.from("user_flags")
    .select("can_comment,is_banned").eq("user_id", user.id).maybeSingle();
  if (flags && (flags.is_banned || !flags.can_comment)) {
    return json(403, { error: "komentiranje nije dopušteno za ovaj račun" });
  }

  // 4) runda mora postojati i biti objavljena
  const { data: disc } = await admin.from("discussions")
    .select("id,status").eq("id", discussion_id).maybeSingle();
  if (!disc || disc.status !== "published") {
    return json(404, { error: "rasprava ne postoji ili nije objavljena" });
  }

  // 5) rate limit po korisniku i po IP hashu (sha256(ip+salt) — sirovi IP
  //    se NE sprema; legitimni interes, opisano u Politici privatnosti)
  const perHour = lim.comments_per_user_hour ?? 10;
  const hourAgo = new Date(Date.now() - 3600_000).toISOString();
  const { count: nUser } = await admin.from("discussion_posts")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id).gte("created_at", hourAgo);
  if ((nUser ?? 0) >= perHour) {
    return json(429, { error: "previše komentara — pokušajte za sat vremena" });
  }
  const ip = (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim();
  const salt = Deno.env.get("COMMENT_IP_SALT") ?? "";
  const ip_hash = ip && salt ? await sha256hex(ip + salt) : null;
  if (ip_hash) {
    const { count: nIp } = await admin.from("discussion_posts")
      .select("id", { count: "exact", head: true })
      .eq("ip_hash", ip_hash).gte("created_at", hourAgo);
    if ((nIp ?? 0) >= perHour) {
      return json(429, { error: "previše komentara s ove adrese" });
    }
  }

  // 6) filter faze 1: sve u pending; sumnjivo odmah flagged
  const status = SUSPECT.some((rx) => rx.test(body)) ? "flagged" : "pending";

  const { data: ins, error: iErr } = await admin.from("discussion_posts")
    .insert({
      discussion_id, author_type: "human", user_id: user.id,
      reply_to, body_hr: body, citations: [], status, ip_hash,
    }).select("id,status").single();
  if (iErr) return json(500, { error: iErr.message });

  // 7) @spomeni — parsiraju se SAMO iz ljudskih postova (po konstrukciji
  //    nema lančane reakcije); red se puni samo uz SUMMONS_ENABLED=true
  let summons = 0;
  if ((Deno.env.get("SUMMONS_ENABLED") ?? "true") === "true") {
    const mentions = [...new Set(
      [...body.matchAll(/@(ai_[a-z]+)\b/g)].map((m) => m[1]))];
    if (mentions.length) {
      const { data: agents } = await admin.from("ai_agents")
        .select("id").in("id", mentions).eq("is_active", true);
      for (const a of agents ?? []) {
        if (a.id === "ai_mod") continue; // moderator se ne poziva
        await admin.from("agent_summons").insert({
          discussion_id, post_id: ins.id, agent_id: a.id, user_id: user.id,
        });
        summons += 1;
      }
    }
  }

  return json(200, {
    ok: true, post_id: ins.id, status: ins.status, summons_queued: summons,
    note: ins.status === "pending"
      ? "komentar čeka odobrenje moderatora" : "komentar je označen za pregled",
  });
});
