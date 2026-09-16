// M67: newsletter prijava s DOUBLE OPT-IN (GDPR + ZEK čl. 107.: privola
// prije slanja; potvrda mailom je dokaz privole) + jednoklik odjava.
// Deploy: supabase functions deploy newsletter --no-verify-jwt
// Secrets: RESEND_API_KEY (slanje maila kroz Resend), opcionalno
//          NEWSLETTER_FROM (default "Burzovni list <newsletter@burzovnilist.com>").
//
// Akcije (POST {action, ...}):
//  - subscribe   {email, lang, source, website}  website = honeypot (bot filter)
//  - confirm     {token}   klik iz potvrdnog maila -> status 'confirmed'
//  - unsubscribe {token}   klik iz bilo kojeg maila -> status 'unsubscribed'
//  - send_issue  {subject, html, text, lang, test_to}  M80: slanje izdanja
//      Autentikacija: header x-api-key = BLOG_API_KEY (isti obrazac kao
//      blog-publish). MASOVNO slanje ide isključivo potvrđenim
//      pretplatnicima (status='confirmed') odabranog jezika. test_to
//      ograničava slanje na TU JEDNU adresu — test izdanja prije masovnog
//      slanja; ako ta adresa nije pretplatnik, test se svejedno šalje (to
//      traži vlasnik s admin ključem) uz opći link za odjavu.
//      Svaki pretplatnik dobiva vlastiti unsubscribe token (RFC 8058).
//
// Privatnost: subscribe UVIJEK vraća istu generičku poruku — endpoint ne
// otkriva postoji li email u listi. Nepotvrđene prijave čisti noćni job
// (30 dana); odjavljeni zapisi se čuvaju kao dokaz i lista isključenja.
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
    "Access-Control-Allow-Headers": "content-type, authorization, x-client-info, apikey",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
};

const SITE = "https://www.burzovnilist.com";
const EMAIL_RX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const RESEND_COOLDOWN_MS = 15 * 60 * 1000; // ponovno slanje potvrde najranije za 15 min

// tekstovi mailova — HR i EN (jezik dolazi iz rute na kojoj je prijava)
function confirmMail(lang: string, confirmUrl: string) {
  if (lang === "en") {
    return {
      subject: "Confirm your newsletter subscription — Burzovni list",
      text: `Hello,

you (or someone using this address) requested the Burzovni list newsletter.
To CONFIRM the subscription, open this link:

${confirmUrl}

If you did not request this, simply ignore this email — without
confirmation nothing will be sent and the request is deleted after 30 days.

Burzovni list — Zagreb Stock Exchange analytics
${SITE}/en · info@burzovnilist.com`,
    };
  }
  return {
    subject: "Potvrdite prijavu na newsletter — Burzovni list",
    text: `Pozdrav,

vi (ili netko s ovom adresom) zatražili ste newsletter Burzovnog lista.
Za POTVRDU prijave otvorite ovaj link:

${confirmUrl}

Ako prijavu niste zatražili, jednostavno zanemarite ovaj email — bez
potvrde se ništa ne šalje, a zahtjev se briše nakon 30 dana.

Burzovni list — analitika Zagrebačke burze
${SITE} · info@burzovnilist.com`,
  };
}

async function sendMail(to: string, subject: string, text: string,
  unsubscribeUrl: string, html?: string): Promise<boolean> {
  const key = Deno.env.get("RESEND_API_KEY");
  if (!key) {
    console.error("RESEND_API_KEY nije postavljen — mail nije poslan");
    return false;
  }
  const from = Deno.env.get("NEWSLETTER_FROM")
    ?? "Burzovni list <newsletter@burzovnilist.com>";
  const body: Record<string, unknown> = {
    from, to: [to], subject, text,
    // RFC 8058 jednoklik odjava — mail klijenti prikazuju vlastiti gumb
    headers: {
      "List-Unsubscribe": `<${unsubscribeUrl}>`,
      "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    },
  };
  if (html) body.html = html;   // M80: izdanja idu HTML + text (multipart)
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { "Authorization": `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) console.error("resend", r.status, (await r.text()).slice(0, 300));
  return r.ok;
}

Deno.serve(async (req) => {
  const CORS = corsFor(req);
  const json = (status: number, body: unknown) =>
    new Response(JSON.stringify(body),
      { status, headers: { ...CORS, "Content-Type": "application/json" } });
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json(405, { error: "POST only" });

  let p: Record<string, unknown>;
  try { p = await req.json(); } catch { return json(400, { error: "nevaljan JSON" }); }
  const action = String(p.action ?? "");

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );
  const T = () => admin.from("newsletter_subscribers");

  if (action === "subscribe") {
    // honeypot: pravi korisnici polje 'website' ne vide; bot ga popuni ->
    // odgovori kao da je uspjelo, bez upisa
    if (String(p.website ?? "").trim() !== "") return json(200, { ok: true });
    const email = String(p.email ?? "").trim().toLowerCase();
    if (!EMAIL_RX.test(email) || email.length > 254) {
      return json(400, { ok: false, error: "email" });
    }
    const lang = p.lang === "en" ? "en" : "hr";
    const source = ["popup", "header", "footer"].includes(String(p.source))
      ? String(p.source) : null;

    const { data: ex } = await T()
      .select("id, status, confirm_token, last_confirm_sent_at")
      .eq("email", email).maybeSingle();

    let confirmToken: string | null = null;
    if (!ex) {
      const { data: ins, error } = await T()
        .insert({ email, lang, source, last_confirm_sent_at: new Date().toISOString() })
        .select("confirm_token").single();
      if (error) {
        // 23505 = utrka dva paralelna submita -> tretiraj kao postojeći pending
        if (error.code !== "23505") { console.error(error.message); return json(500, { ok: false }); }
      } else confirmToken = ins.confirm_token;
    } else if (ex.status === "confirmed") {
      // već pretplaćen — ista generička poruka (bez otkrivanja stanja)
    } else {
      // pending ili unsubscribed (ponovna prijava traži NOVU potvrdu —
      // stara privola je povučena); cooldown protiv mail-bombinga
      const last = ex.last_confirm_sent_at ? Date.parse(ex.last_confirm_sent_at) : 0;
      if (Date.now() - last >= RESEND_COOLDOWN_MS) {
        const upd: Record<string, unknown> = {
          lang, last_confirm_sent_at: new Date().toISOString(),
        };
        if (ex.status === "unsubscribed") {
          upd.status = "pending";
          upd.unsubscribed_at = null;
          upd.confirmed_at = null;
        }
        const { error } = await T().update(upd).eq("id", ex.id);
        if (!error) confirmToken = ex.confirm_token;
      }
    }

    if (confirmToken) {
      const confirmUrl = lang === "en"
        ? `${SITE}/en/newsletter/confirm?token=${confirmToken}`
        : `${SITE}/newsletter/potvrda?token=${confirmToken}`;
      const m = confirmMail(lang, confirmUrl);
      // potvrdni mail nosi i link za odjavu zahtjeva (isti confirm flow ga
      // ne treba, ali RFC 8058 header mora negdje voditi) — koristimo
      // unsubscribe token tek nakon potvrde; ovdje link na politiku
      const sent = await sendMail(email, m.subject, m.text,
        `${SITE}/newsletter/odjava`);
      if (!sent && !Deno.env.get("RESEND_API_KEY")) {
        return json(503, { ok: false, error: "mail servis nije konfiguriran" });
      }
    }
    return json(200, { ok: true });
  }

  if (action === "confirm" || action === "unsubscribe") {
    const token = String(p.token ?? "");
    if (!/^[0-9a-f-]{36}$/.test(token)) return json(400, { ok: false, error: "token" });
    const col = action === "confirm" ? "confirm_token" : "unsubscribe_token";
    const { data: row } = await T()
      .select("id, status").eq(col, token).maybeSingle();
    if (!row) return json(404, { ok: false, error: "nepoznat token" });

    if (action === "confirm") {
      if (row.status === "confirmed") return json(200, { ok: true, already: true });
      if (row.status === "unsubscribed") return json(404, { ok: false, error: "nepoznat token" });
      const { error } = await T()
        .update({ status: "confirmed", confirmed_at: new Date().toISOString() })
        .eq("id", row.id);
      if (error) { console.error(error.message); return json(500, { ok: false }); }
      return json(200, { ok: true });
    }
    // unsubscribe — idempotentno; zapis OSTAJE (dokaz + lista isključenja)
    if (row.status === "unsubscribed") return json(200, { ok: true, already: true });
    const { error } = await T()
      .update({ status: "unsubscribed", unsubscribed_at: new Date().toISOString() })
      .eq("id", row.id);
    if (error) { console.error(error.message); return json(500, { ok: false }); }
    return json(200, { ok: true });
  }

  // M80: slanje izdanja newslettera (admin akcija, x-api-key)
  if (action === "send_issue") {
    const key = req.headers.get("x-api-key");
    if (!key || key !== Deno.env.get("BLOG_API_KEY")) {
      return json(401, { error: "neautoriziran" });
    }
    const subject = String(p.subject ?? "").trim();
    const html = String(p.html ?? "");
    const text = String(p.text ?? "");
    const lang = p.lang === "en" ? "en" : "hr";
    const testTo = p.test_to == null ? null : String(p.test_to).trim().toLowerCase();
    if (!subject || subject.length > 200) {
      return json(400, { error: "subject: obavezan, <=200 znakova" });
    }
    if (!text.trim()) return json(400, { error: "text: obavezan (plain-text verzija)" });
    if (testTo && !EMAIL_RX.test(testTo)) return json(400, { error: "test_to: nevaljan email" });

    // primatelji: SAMO potvrđeni pretplatnici; test_to sužava na jednu adresu
    let q = T().select("email, unsubscribe_token, lang")
      .eq("status", "confirmed").eq("lang", lang);
    if (testTo) q = q.eq("email", testTo);
    const { data: found, error: qErr } = await q;
    if (qErr) { console.error(qErr.message); return json(500, { error: "upit" }); }
    let rows = found ?? [];
    // TEST na adresu koja još nije pretplatnik: dopušteno samo uz test_to
    // (jednokratna provjera izgleda izdanja prije masovnog slanja, poziva
    // je vlasnik s admin ključem). Odjava tada vodi na opću stranicu jer
    // token ne postoji. Masovno slanje ovu granu NEMA.
    let unregisteredTest = false;
    if (!rows.length && testTo) {
      rows = [{ email: testTo, unsubscribe_token: null, lang }];
      unregisteredTest = true;
    }
    if (!rows.length) {
      return json(404, { error: `nema potvrđenih pretplatnika za jezik '${lang}'` });
    }
    if (!Deno.env.get("RESEND_API_KEY")) {
      return json(503, { error: "mail servis nije konfiguriran" });
    }

    let sent = 0;
    const failed: string[] = [];
    for (const r of rows) {
      const base = lang === "en"
        ? `${SITE}/en/newsletter/unsubscribe`
        : `${SITE}/newsletter/odjava`;
      const unsubUrl = r.unsubscribe_token
        ? `${base}?token=${r.unsubscribe_token}`
        : base;   // test na neregistriranu adresu — opća stranica odjave
      // svaki primatelj dobiva SVOJ token u tijelu i u zaglavlju
      const okMail = await sendMail(
        r.email, subject,
        text.replaceAll("{{UNSUBSCRIBE_URL}}", unsubUrl),
        unsubUrl,
        html ? html.replaceAll("{{UNSUBSCRIBE_URL}}", unsubUrl) : undefined);
      if (okMail) sent += 1; else failed.push(r.email);
      // Resend dopušta 2 zahtjeva/s — razmak čuva rate limit na većim listama
      if (rows.length > 1) await new Promise((res) => setTimeout(res, 600));
    }
    return json(200, {
      ok: true, recipients: rows.length, sent,
      failed: failed.length, test: Boolean(testTo),
      note: unregisteredTest
        ? `${testTo} nije potvrđeni pretplatnik — poslan test s općim linkom za odjavu`
        : undefined,
    });
  }

  return json(400, { error: "nepoznata akcija" });
});
