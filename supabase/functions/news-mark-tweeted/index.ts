// M30: Cowork agent označava vijest kao iskorištenu za X objavu
// (tweeted=true) — ista vijest se ne pretvara u tweet dvaput.
// Deploy: supabase functions deploy news-mark-tweeted --no-verify-jwt
// Secret: BLOG_API_KEY. Agent NEMA direktan pristup bazi — samo ovaj endpoint.
import { createClient } from "npm:@supabase/supabase-js@2";

// CORS: samo vlastite domene (audit M36: '*' je presirok) — browser pozivi
// dolaze iskljucivo s burzovnilist.com; server-server pozivi (pipeline,
// agent, hookovi) ne salju Origin pa ih suzavanje ne dira.
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
  const id = String(p.id ?? "").trim();
  if (!/^[0-9a-f-]{36}$/.test(id)) return json(400, { error: "id: nevaljan uuid" });

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );

  const { data, error } = await admin.from("news_items")
    .update({ tweeted: true })
    .eq("id", id).eq("status", "published")
    .select("id");
  if (error) return json(500, { error: error.message });
  if (!data?.length) return json(404, { error: "vijest ne postoji ili nije objavljena" });

  return json(200, { ok: true, id });
});
