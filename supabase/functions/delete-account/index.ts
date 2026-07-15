// GDPR brisanje računa (M26). Deploy: supabase functions deploy delete-account
// Service role key je SAMO secret ove funkcije (SUPABASE_SERVICE_ROLE_KEY je
// automatski dostupan u Edge runtimeu) — NIKAD u frontend.
//
// Sigurnosni model: funkcija je autorizirana ISKLJUČIVO JWT-om pozivatelja
// (Authorization: Bearer <access_token>) i briše ISKLJUČIVO auth.uid()
// pozivatelja — ne prima nikakav user_id parametar. Cascade na
// profiles/portfolios/portfolio_positions radi baza (on delete cascade).
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "POST only" }),
      { status: 405, headers: { ...CORS, "Content-Type": "application/json" } });
  }

  const url = Deno.env.get("SUPABASE_URL")!;
  const anon = Deno.env.get("SUPABASE_ANON_KEY")!;
  const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  // 1) identitet pozivatelja iz NJEGOVOG JWT-a (verificira Supabase Auth)
  const authHeader = req.headers.get("Authorization") ?? "";
  const caller = createClient(url, anon, {
    global: { headers: { Authorization: authHeader } },
  });
  const { data: { user }, error: userErr } = await caller.auth.getUser();
  if (userErr || !user) {
    return new Response(JSON.stringify({ error: "neautoriziran" }),
      { status: 401, headers: { ...CORS, "Content-Type": "application/json" } });
  }

  // 2) admin brisanje ISKLJUČIVO tog korisnika (auth.uid() pozivatelja)
  const admin = createClient(url, service, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { error: delErr } = await admin.auth.admin.deleteUser(user.id);
  if (delErr) {
    return new Response(JSON.stringify({ error: delErr.message }),
      { status: 500, headers: { ...CORS, "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: true }),
    { status: 200, headers: { ...CORS, "Content-Type": "application/json" } });
});
