// M30: prijem auto-generiranih vijesti iz noćnog EOD pipelinea.
// Deploy: supabase functions deploy news-ingest --no-verify-jwt
// Secret: BLOG_API_KEY (isti kao blog-publish — jedan ključ za agent/pipeline).
//
// Pipeline NEMA direktan write pristup bazi — samo ovaj endpoint. Ključ se
// provjerava PRIJE ičega; service role SAMO unutar functiona. Sve vijesti
// ulaze kao DRAFT (nikad auto-publish — admin pregledava prije objave).
// Dedup po auto_source_ref (unique indeks): ponovni run istog pipelinea
// preskače postojeće zapise umjesto da ih duplicira.
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body),
    { status, headers: { ...CORS, "Content-Type": "application/json" } });

const CATEGORIES = ["novo_izvjesce", "dividenda", "promjena_cijene", "opce"];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "POST only" });

  const key = req.headers.get("x-api-key");
  if (!key || key !== Deno.env.get("BLOG_API_KEY")) {
    return json(401, { error: "neautoriziran" });
  }

  let p: Record<string, unknown>;
  try { p = await req.json(); } catch { return json(400, { error: "nevaljan JSON" }); }
  const items = Array.isArray(p.items) ? p.items : [];
  if (!items.length) return json(400, { error: "items: prazan popis" });
  if (items.length > 200) return json(400, { error: "items: max 200 po pozivu" });

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );

  let inserted = 0, skipped = 0;
  const errors: string[] = [];
  for (const raw of items) {
    const it = raw as Record<string, unknown>;
    const headline = String(it.headline ?? "").trim();
    const category = String(it.category ?? "");
    const link_path = String(it.link_path ?? "");
    const auto_source_ref = String(it.auto_source_ref ?? "").trim();
    if (!headline || headline.length > 120) { errors.push(`headline: 1-120 znakova (${auto_source_ref})`); continue; }
    if (!CATEGORIES.includes(category)) { errors.push(`category: nevaljana (${auto_source_ref})`); continue; }
    if (!/^\//.test(link_path)) { errors.push(`link_path: mora biti interna ruta (${auto_source_ref})`); continue; }
    if (!auto_source_ref) { errors.push("auto_source_ref: obavezan za auto vijesti"); continue; }

    // dedup: postoji li već zapis s istim auto_source_ref?
    const { data: existing } = await admin.from("news_items")
      .select("id").eq("auto_source_ref", auto_source_ref).maybeSingle();
    if (existing) { skipped += 1; continue; }

    const { error } = await admin.from("news_items").insert({
      ticker: it.ticker == null ? null : String(it.ticker),
      category, headline,
      body: it.body == null ? null : String(it.body),
      link_path,
      source_type: "auto",
      auto_source_ref,
      status: "draft", // NIKAD auto-publish
    });
    if (error) {
      // 23505 = unique violation (utrka s paralelnim runom) -> dedup, ne greška
      if (error.code === "23505") skipped += 1;
      else errors.push(`${auto_source_ref}: ${error.message}`);
    } else inserted += 1;
  }

  return json(200, { ok: true, inserted, skipped, errors });
});
