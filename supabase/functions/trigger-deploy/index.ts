// M27: rebuild produkcije iz admin sučelja (na "Objavi"/"Ažuriraj").
// Deploy: supabase functions deploy trigger-deploy
// Autorizacija: JWT pozivatelja MORA pripadati adminu (profiles.is_admin);
// deploy hook URL ostaje secret Edge Functiona — nikad u frontend.
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
    "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
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

  const caller = createClient(
    Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!,
    { global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } } },
  );
  const { data: { user } } = await caller.auth.getUser();
  if (!user) return json(401, { error: "neautoriziran" });
  const { data: prof } = await caller.from("profiles")
    .select("is_admin").eq("id", user.id).maybeSingle();
  if (!prof?.is_admin) return json(403, { error: "nije admin" });

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );
  let slug = "";
  try { slug = String((await req.json())?.slug ?? ""); } catch { /* opcionalno */ }
  await admin.from("blog_publish_log").insert(
    { slug: slug || "(admin-ui)", status: "published", via: "admin_ui" });

  const hook = Deno.env.get("VERCEL_DEPLOY_HOOK_URL");
  if (!hook) return json(500, { error: "VERCEL_DEPLOY_HOOK_URL secret nije postavljen" });
  const r = await fetch(hook, { method: "POST" });
  return json(200, { ok: true, deploy_triggered: r.ok });
});
