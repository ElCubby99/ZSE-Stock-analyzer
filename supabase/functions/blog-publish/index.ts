// M27: automatizirano objavljivanje blog postova (Cowork agent).
// Deploy: supabase functions deploy blog-publish --no-verify-jwt
// Secreti: BLOG_API_KEY (nasumični dugi string), VERCEL_DEPLOY_HOOK_URL.
//
// Autentikacija: statički admin API ključ u headeru `x-api-key` — provjerava
// se PRIJE ičega; service role key se koristi SAMO unutar functiona (nikad
// se ne vraća niti loguje). Upsert po slugu; published_at = now() pri prvoj
// objavi; nakon uspjeha okida Vercel deploy hook (rebuild s novim postom).
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

const SLUG_RX = /^[a-z0-9]+(-[a-z0-9]+)*$/;

Deno.serve(async (req) => {
  const CORS = corsFor(req);
  const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body),
      { status, headers: { ...CORS, "Content-Type": "application/json" } });
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "POST only" });

  // 1) API ključ — bez detalja u poruci greške
  const key = req.headers.get("x-api-key");
  if (!key || key !== Deno.env.get("BLOG_API_KEY")) {
    return json(401, { error: "neautoriziran" });
  }

  // 2) payload + server-side validacija (ne samo UI)
  let p: Record<string, unknown>;
  try { p = await req.json(); } catch { return json(400, { error: "nevaljan JSON" }); }
  const slug = String(p.slug ?? "").trim();
  const title = String(p.title ?? "").trim();
  const content_md = String(p.content_md ?? "");
  const meta_description = p.meta_description == null ? null : String(p.meta_description);
  const status = String(p.status ?? "draft");
  const tags = Array.isArray(p.tags) ? p.tags.map(String).slice(0, 20) : [];
  const cover_image_url = p.cover_image_url == null ? null : String(p.cover_image_url);

  if (!SLUG_RX.test(slug)) return json(400, { error: "slug: mora biti kebab-case ([a-z0-9-])" });
  if (!title || title.length > 200) return json(400, { error: "title: obavezan, <=200 znakova" });
  if (!content_md.trim()) return json(400, { error: "content_md: obavezan" });
  if (meta_description && meta_description.length > 160) {
    return json(400, { error: "meta_description: hard cap 160 znakova" });
  }
  if (!["draft", "published"].includes(status)) {
    return json(400, { error: "status: draft | published" });
  }
  if (cover_image_url && !/^https:\/\//.test(cover_image_url)) {
    return json(400, { error: "cover_image_url: mora biti https URL" });
  }

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );

  // 3) upsert po slugu; published_at samo pri PRVOJ objavi
  const { data: existing } = await admin.from("blog_posts")
    .select("id, published_at").eq("slug", slug).maybeSingle();
  const row: Record<string, unknown> = {
    slug, title, meta_description, content_md, tags, cover_image_url, status,
  };
  if (status === "published" && !existing?.published_at) {
    row.published_at = new Date().toISOString();
  }
  const q = existing
    ? admin.from("blog_posts").update(row).eq("id", existing.id)
    : admin.from("blog_posts").insert(row);
  const { error } = await q;
  if (error) return json(500, { error: error.message });

  await admin.from("blog_publish_log").insert({ slug, status, via: "api_key" });

  // 4) deploy hook (rebuild) — samo kad je objavljeno
  let deploy_triggered = false;
  const hook = Deno.env.get("VERCEL_DEPLOY_HOOK_URL");
  if (status === "published" && hook) {
    try {
      const r = await fetch(hook, { method: "POST" });
      deploy_triggered = r.ok;
    } catch { deploy_triggered = false; }
  }

  return json(200, { ok: true, slug, status, deploy_triggered });
});
