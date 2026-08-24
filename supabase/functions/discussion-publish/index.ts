// NALOG M30: upis AI runde rasprave (orkestrator / pipeline).
// Deploy: supabase functions deploy discussion-publish --no-verify-jwt
// Secret: BLOG_API_KEY (isti ključ kao blog-publish — jedan ključ za pipeline).
//
// Payload: { discussion: {ticker, round_no, trigger, status?, data_snapshot,
//            summary_hr, summary_en, agree_points, disagree_points,
//            questions_for_humans},
//            posts: [{agent_id, volley_no, body_hr, body_en, citations,
//                     model_used?, tokens_in?, tokens_out?, cost_usd?}],
//            calls: [{agent_id, stance, horizon_months, price_at_call,
//                     zone_low, zone_high, invalidation_condition}] }
// Upsert po (ticker, round_no): AI postovi i calls te runde se ZAMJENJUJU,
// ljudski komentari ostaju netaknuti.
//
// Validacija PRIJE upisa (točka 3 naloga): AI post bez citata se odbija;
// zabranjene riječi (MAR) ruše cijeli payload; duljina max 2600 znakova.
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
    "Access-Control-Allow-Headers": "content-type, x-api-key",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
};

// MAR filter: ove riječi u AI outputu ne postoje (hrvatski i engleski).
// Granice riječi — "otkup" i "prodaja imovine" ne smiju lažno okinuti.
const FORBIDDEN = [
  /\bkupi(te)?\b/i, /\bprodaj(te)?\b/i, /\bpreporu[čc]ujem\b/i,
  /\bpreporu[čc]amo\b/i, /\bciljna cijena\b/i, /\btarget price\b/i,
  /\bstrong (buy|sell)\b/i, /\b(buy|sell) rating\b/i,
];
const forbiddenHit = (s: string) =>
  FORBIDDEN.find((rx) => rx.test(s || ""))?.source ?? null;

const MAX_BODY = 2600; // ~250 riječi + fusnote

Deno.serve(async (req) => {
  const CORS = corsFor(req);
  const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body),
      { status, headers: { ...CORS, "Content-Type": "application/json" } });
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "POST only" });

  const key = req.headers.get("x-api-key");
  if (!key || key !== Deno.env.get("BLOG_API_KEY")) {
    return json(401, { error: "neautoriziran" });
  }

  let p: Record<string, unknown>;
  try { p = await req.json(); } catch { return json(400, { error: "nevaljan JSON" }); }
  const d = (p.discussion ?? {}) as Record<string, unknown>;
  const posts = Array.isArray(p.posts) ? p.posts as Record<string, unknown>[] : [];
  const calls = Array.isArray(p.calls) ? p.calls as Record<string, unknown>[] : [];

  const ticker = String(d.ticker ?? "").toUpperCase();
  const round_no = Number(d.round_no ?? 0);
  if (!/^[A-Z0-9]{1,8}$/.test(ticker)) return json(400, { error: "ticker" });
  if (!Number.isInteger(round_no) || round_no < 1) return json(400, { error: "round_no" });
  if (!d.data_snapshot) return json(400, { error: "data_snapshot: obavezan" });
  if (!posts.length) return json(400, { error: "posts: prazno" });

  // validacija postova (sve-ili-ništa: jedan nevaljan post ruši payload)
  for (const post of posts) {
    const agent = String(post.agent_id ?? "");
    const body_hr = String(post.body_hr ?? "");
    const cits = Array.isArray(post.citations) ? post.citations : [];
    if (!agent) return json(400, { error: "post bez agent_id" });
    if (!body_hr.trim()) return json(400, { error: `${agent}: prazan body_hr` });
    if (body_hr.length > MAX_BODY || String(post.body_en ?? "").length > MAX_BODY) {
      return json(400, { error: `${agent}: post duži od ${MAX_BODY} znakova` });
    }
    if (!cits.length) return json(400, { error: `${agent}: AI post bez citata` });
    const hit = forbiddenHit(body_hr) || forbiddenHit(String(post.body_en ?? ""))
      || forbiddenHit(String(d.summary_hr ?? "")) || forbiddenHit(String(d.summary_en ?? ""));
    if (hit) return json(400, { error: `MAR filter: zabranjen izraz (${hit})` });
  }
  for (const c of calls) {
    if (!["below_zone", "in_zone", "above_zone"].includes(String(c.stance))) {
      return json(400, { error: `call ${c.agent_id}: stance` });
    }
    if (!String(c.invalidation_condition ?? "").trim()) {
      return json(400, { error: `call ${c.agent_id}: invalidation_condition obavezan` });
    }
  }

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );

  // upsert runde po (ticker, round_no)
  const { data: existing } = await admin.from("discussions")
    .select("id").eq("ticker", ticker).eq("round_no", round_no).maybeSingle();
  const row: Record<string, unknown> = {
    ticker, round_no,
    trigger: ["scheduled", "new_report", "dividend", "manual"]
      .includes(String(d.trigger)) ? d.trigger : "manual",
    status: ["draft", "published", "archived"].includes(String(d.status))
      ? d.status : "draft",
    data_snapshot: d.data_snapshot,
    summary_hr: d.summary_hr ?? null, summary_en: d.summary_en ?? null,
    agree_points: d.agree_points ?? null,
    disagree_points: d.disagree_points ?? null,
    questions_for_humans: d.questions_for_humans ?? null,
  };
  let discId: string;
  if (existing) {
    const { error } = await admin.from("discussions").update(row).eq("id", existing.id);
    if (error) return json(500, { error: error.message });
    discId = existing.id;
    // zamjena AI sadržaja runde; ljudski postovi ostaju
    await admin.from("discussion_posts").delete()
      .eq("discussion_id", discId).eq("author_type", "ai");
    await admin.from("agent_calls").delete().eq("discussion_id", discId);
  } else {
    const { data: ins, error } = await admin.from("discussions")
      .insert(row).select("id").single();
    if (error) return json(500, { error: error.message });
    discId = ins.id;
  }

  const postRows = posts.map((post) => ({
    discussion_id: discId, author_type: "ai",
    agent_id: post.agent_id, volley_no: post.volley_no ?? null,
    body_hr: post.body_hr, body_en: post.body_en ?? null,
    citations: post.citations, status: "published",
    model_used: post.model_used ?? null,
    tokens_in: post.tokens_in ?? null, tokens_out: post.tokens_out ?? null,
    cost_usd: post.cost_usd ?? null,
  }));
  const { error: pErr } = await admin.from("discussion_posts").insert(postRows);
  if (pErr) return json(500, { error: pErr.message });

  if (calls.length) {
    const callRows = calls.map((c) => ({
      discussion_id: discId, agent_id: c.agent_id, ticker,
      stance: c.stance, horizon_months: c.horizon_months ?? 12,
      price_at_call: c.price_at_call ?? null,
      zone_low: c.zone_low ?? null, zone_high: c.zone_high ?? null,
      invalidation_condition: c.invalidation_condition,
    }));
    const { error: cErr } = await admin.from("agent_calls").insert(callRows);
    if (cErr) return json(500, { error: cErr.message });
  }

  return json(200, { ok: true, discussion_id: discId, ticker, round_no,
    n_posts: postRows.length, n_calls: calls.length });
});
