// M30: izvor sadržaja za X (Twitter) objave — Cowork agent poziva GET i
// dobiva OBJAVLJENE vijesti koje još nisu tweetane (tweeted=false).
// Deploy: supabase functions deploy news-list --no-verify-jwt
// Secret: BLOG_API_KEY. Agent NEMA direktan pristup bazi — samo ovaj endpoint.
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-key",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body),
    { status, headers: { ...CORS, "Content-Type": "application/json" } });

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "GET") return json(405, { error: "GET only" });

  const key = req.headers.get("x-api-key");
  if (!key || key !== Deno.env.get("BLOG_API_KEY")) {
    return json(401, { error: "neautoriziran" });
  }

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );

  const { data, error } = await admin.from("news_items")
    .select("id, ticker, category, headline, body, link_path, published_at")
    .eq("status", "published").eq("tweeted", false)
    .order("published_at", { ascending: false })
    .limit(50);
  if (error) return json(500, { error: error.message });

  return json(200, { ok: true, items: data });
});
