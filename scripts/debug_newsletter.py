#!/usr/bin/env python3
"""M67 jednokratna provjera: je li Edge Function 'newsletter' deployana i
šalje li Resend potvrdni mail. Ukloniti nakon potvrde.

1) s live stranice izvuče javni Supabase URL + anon key (iz JS bundlea)
2) pozove funkciju s nepostojećim confirm tokenom -> naš JSON = deployano;
   Supabase 'Function not found' = NIJE deployano
3) ako je deployana: prijavi boris.cubric@gmail.com (double opt-in ->
   stiže SAMO potvrdni mail; ništa nije pretplaćeno bez klika)
"""
import json
import re
import sys

import requests

SITE = "https://www.burzovnilist.com"
TEST_EMAIL = "boris.cubric@gmail.com"


def main() -> int:
    html = requests.get(SITE, timeout=30).text
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not m:
        print("NE MOGU naći JS bundle na", SITE)
        return 1
    js = requests.get(SITE + m.group(1), timeout=30).text
    mu = re.search(r'https://([a-z0-9]+)\.supabase\.co', js)
    mk = re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', js)
    if not mu:
        print("NE MOGU naći Supabase URL u bundleu (VITE_SUPABASE_URL nije u buildu?)")
        return 1
    base = f"https://{mu.group(1)}.supabase.co"
    print("Supabase projekt:", mu.group(1), "| anon key nađen:", bool(mk))
    headers = {"Content-Type": "application/json"}
    if mk:
        headers["Authorization"] = f"Bearer {mk.group(0)}"
        headers["apikey"] = mk.group(0)

    fn = f"{base}/functions/v1/newsletter"
    r = requests.post(fn, headers=headers, timeout=30, json={
        "action": "confirm", "token": "00000000-0000-0000-0000-000000000000"})
    print("confirm (nepostojeći token):", r.status_code, r.text[:200])
    body = {}
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        pass
    deployed = r.status_code in (400, 404) and body.get("error") in (
        "nepoznat token", "token")
    if not deployed:
        print("=> funkcija 'newsletter' NIJE deployana (ili vraća neočekivano)")
        return 0

    print("=> funkcija JE deployana; šaljem probnu prijavu za", TEST_EMAIL)
    r = requests.post(fn, headers=headers, timeout=30, json={
        "action": "subscribe", "email": TEST_EMAIL,
        "lang": "hr", "source": "header", "website": ""})
    print("subscribe:", r.status_code, r.text[:300])
    if r.status_code == 200:
        print("=> OK — potvrdni mail bi trebao stići (Resend); klik na link "
              "u mailu dovršava double opt-in")
    elif r.status_code == 503:
        print("=> funkcija radi, ali RESEND_API_KEY nije vidljiv funkciji "
              "(secret dodan NAKON deploya? redeploy funkcije učitava secrete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
