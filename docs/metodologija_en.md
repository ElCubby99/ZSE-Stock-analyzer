# How we estimate value

*Everything below describes what the system actually does; where something
is only planned, it says so.*

## What this is — and what it is not

Burzovni list is an analytics platform: for every covered Zagreb Stock
Exchange stock we show public data, financials from official filings and our
fair-value estimate together with an explanation of how it was produced.
**None of it is a recommendation to buy or sell, nor investment advice.** We
show the numbers, the methods and the assumptions — the conclusion is always
the reader's.

## Three approaches to value — and why every company has its own anchor

In practice, company value is measured in three ways:

1. **Income approach**: what the company's future cash is worth (DCF), the
   dividends it pays (DDM), or the return earned on its own equity above the
   required return (justified P/B, residual income).
2. **Market approach**: what the market pays for similar companies — a
   single "peer comparison" method that looks at the company through several
   lenses (P/E, EV/EBITDA, EV/EBIT, P/B) against comparables. The lenses are
   inputs to that method, not separate methods.
3. **Asset approach**: the sum of the parts (SOTP) — for holdings and groups
   with separable businesses.

No single approach is universally best — which is why every **type** of
company has its own **anchor** (primary method), while the others serve as
cross-checks:

- **Holding company** (e.g. Adris, Končar): value consists of stakes in
  other companies → the anchor is the **sum of the parts**. Subsidiaries
  with their own reliable analysis enter at our estimate, the rest at market
  price — both figures are always shown.
- **Bank / insurer**: the business is earning a return on capital → the
  anchor is **return on equity** (justified P/B, residual income).
- **Industrial with contracted business** (backlog, guidance): the anchor
  is a **DCF** with growth derived from that signal.
- **Industrial without a forward signal**: the anchor is the **peer
  comparison**.
- **Cyclical company** (low return on capital, leverage): caution —
  guidance-based DCF when management publishes numbers, otherwise book
  equity; EV/EBITDA is avoided because it flatters leveraged companies with
  high depreciation.
- **Tourism**: the sector is compared on EV/EBITDA (with a note on leases).

The fair-value zone = **anchor ± sensitivity to the key assumption** (e.g.
cost of equity ±1 percentage point) — not the range of all methods, because
a single weak method would stretch the zone into uselessness.

## How we choose parameters

- **Cost of equity (r) — full breakdown (v3)**: r = rf + β × ERP + CRP
  (+ illiquidity premium). Components: **rf** is the euro risk-free yield
  (10-year German Bund) — deliberately NOT the Croatian curve, which
  already carries the Croatian spread; **ERP** is Damodaran's mature-market
  premium (without a country premium); **CRP** is a small, separate premium
  for Croatian risk appropriate to an investment-grade eurozone member
  ('A-'/A3), capped at ≤ 1.5 percentage points and added exactly once (it
  is not multiplied by beta). Country risk is thus charged in ONE place —
  it used to be inadvertently counted twice (in the risk-free rate and
  inside the market premium), which systematically depressed our estimates;
  see "Lessons learned" below. Each component carries its own source and
  entry date on the stock page. *Planned, not yet active: exporters earning
  most of their revenue in developed markets deserve a lower CRP — we will
  weight the premium by revenue geography.*
- **Beta discipline (v2.2)** — a regression beta from the exchange series
  (weekly returns vs CROBEX) is used **only above a liquidity threshold**
  (≥60% of days traded and ≥ €1,000 average daily turnover), because thin
  trading statistically depresses beta and artificially flatters the
  estimate (stale-price bias). Above the threshold the Blume adjustment
  applies (0.67·β + 0.33·1); below it, or without a series, a **sector
  beta** is used (Damodaran, Europe), relevered with the company's leverage
  where debt is known. The final beta is bounded to **[0.7, 1.8]**. The
  beta's origin (regression / sector / clamp) is visible next to every
  estimate. **R² credibility (M47)**: beta measures how much a stock SWINGS
  relative to the market, not how fundamentally "good" the company is — a
  stock that rose strongly and volatilely gets a high beta even with
  excellent results. When the regression has a low R² (the market explains
  less than 50% of the stock's movement), the beta is statistically noisy,
  so the Blume regression beta is blended with the sector beta in proportion
  to how much the market explains (weight = R²/0.5). This keeps high momentum
  from pushing the required return above what fundamentals justify (e.g.
  KOEI: R² 0.35 lowers beta from ~1.57 to ~1.36).
- **Illiquidity premium (v2.2)** — stocks below the liquidity threshold get
  +1.0 to +2.0 percentage points added to the cost of equity (graded by
  liquidity): exiting a thinly traded position carries a real cost. It is
  shown as a separate component in the assumptions.
- **Input freshness — TTM (v3)**: where a company publishes quarterly
  reports, earnings, revenue and ROE are computed over the **trailing 12
  months** (last annual + this year's quarters − last year's quarters;
  quarterly reports are cumulative and unaudited). Strict gates: if the
  quarterly series is inconsistent with the audited annual report
  (deviation > 5%) or there is no prior-year comparison, TTM is NOT built —
  the annual figure is used with a visible `annual data` tag and a reason.
  Balance-sheet items (equity, debt) are taken as of the last published
  date.
- **Growth phase (g1) — a composite of three signals (v3.1)**: g1 is the
  **median** of three signals, all derived exclusively from published
  numbers: (1) **series** — the three-year revenue CAGR (or earnings CAGR
  where no revenue series exists) from our database, computed only with
  **at least three annual reports**; (2) **sustainable growth** — ROE × the
  share of profit not paid out as dividends (payout after the regulatory
  cap; a company without dividends retains all profit); (3) the **terminal
  anchor** (2.5% or 4%, by method type). The cap is applied **after** the
  median: 10% when a series exists, 8% without one (tagged `short series`).
  **A single year-on-year comparison (TTM vs last year) is never a
  standalone source of a growth rate** — one year measures one-off effects
  and base effects, so it is shown only as context. g1 cannot be negative
  unless a ≥3-year series proves a multi-year contraction, and it is
  **always at least 0.5 percentage points below the cost of equity r**
  (valuation formulas break when growth approaches the discount rate).
  After g1 comes a linear fade to terminal g over 5 years, with no jumps.
  All three signals, which one decided, and any caps are spelled out in the
  Assumptions on each stock's page. Manual "forward estimates" (backlog,
  guidance, management expectations) are **not used** for the growth rate —
  numeric guidance may only serve as a substitute cash-flow input where the
  cash-flow statement has not been published, and is then clearly tagged.
- **ROE for equity methods (v3)**: we use the **higher of (three-year
  median of annual ROE, TTM ROE × 0.9)** — the median stabilizes one
  atypical year (e.g. COVID or a one-off gain), while the 0.9 factor keeps
  caution toward a fresh, unaudited figure. Without quarterly data: annual
  ROE.
- **Long-run growth (g)** — tied to the economy, not to wishes: 4% nominal
  for the DCF terminal (real growth + inflation), a more conservative 2.5%
  for equity methods. No company can grow faster than its economy
  "forever".
- **Fair-value zone = median of qualified methods (v3)**: the zone is no
  longer the range of one "primary" method. Every method with a positive
  value, sufficient input confidence and stable sensitivity qualifies; the
  zone midpoint is the **median** of their values, and the width comes from
  the sensitivity of the primary anchor (r ± 1 percentage point). If two
  methods agree with each other (±20%) while the incumbent anchor deviates
  materially (>30%), the anchor loses primacy — visibly recorded next to
  the estimate.
- **Sustainable-dividend test → dividend floor (v3.1)**: for dividend
  payers the zone passes an internal check — the yield of the
  **sustainable** dividend at the zone's lower bound must not exceed r − g
  (the Gordon lower bound: if the dividend alone earns more at some price
  than an investor demands for the risk, that price is too low to be fair).
  The threshold uses the same growth rate the zone was computed with (2.5%
  for equity methods, 4% for DCF/DDM anchors) — a threshold with a
  different rate would falsely refute the zone merely through the
  difference in our own assumptions. When the zone fails the test, the test
  is **no longer a veto but an input**: the Gordon value of the sustainable
  dividend V_div = D_sust ÷ (r − g) joins the qualified methods (high
  confidence — the dividend is the hardest publicly available evidence),
  the zone is recomputed and its lower bound raised at least to V_div (the
  **dividend floor**), and the test is re-run on the new zone. The full
  walkthrough with that stock's numbers is on its page. The mirror test
  also exists (a too-high zone with payout ~100%) — then V_div enters the
  median and pulls the zone down. Zone suspension ("recalibrating") as an
  outcome **does not exist**: every stock with data has a published
  fair-value zone; where methods disagree strongly, the zone is wider and
  clearly tagged.
- **Negligible free float (v3)**: when the top-10 shareholders hold >90%
  (e.g. INA), the price forms in negligible turnover under dominant owners
  — the gap between price and zone is then NOT informative, carries a
  prominent note and is excluded from the aggregate "market temperature".
- **Parents with their own business — SOTP rules (v3)**: a parent's
  sum-of-the-parts has a documented rule for EVERY component. Listed
  subsidiaries enter at our fair estimate (or market capitalization where
  our estimate does not qualify); the **parent's own operating business
  (standalone)** is valued exclusively from the parent's **separate
  (unconsolidated) financial statements**, with dividend income from
  subsidiaries mandatorily excluded (otherwise a subsidiary would be
  counted twice) — until the separate statements are in our database the
  component carries an "in progress" status and stays out of the sum (it is
  not approximated from consolidated figures). **Unlisted stakes and joint
  ventures** are valued at the share of book value from the report's notes
  (equity method), and only absent that figure at a conservative multiple
  of published profit — always tagged as an assumption, with a source. Zone
  recomputation follows the **dependency order** (subsidiaries first, then
  parents), so a parent never inherits a subsidiary's stale zone; a cycle
  in the ownership graph is reported as an error. Coverage of a parent's
  announced dividend includes the expected dividend inflows from
  subsidiaries (factually from their last approved payouts × our stake).
- **Share classes — one company value (v3)**: for companies with two
  classes (ordinary and preferred: ADRS/ADRS2, KODT/KODT2, CROS/CROS2,
  PLAG/PLAG2) the fair-value zone is computed for the COMPANY and then
  apportioned to the classes by the **market-observed class price ratio** —
  the median daily ratio over the last 5 years, using only days when both
  classes actually traded (at least 30 observations; otherwise the
  dividend-rights ratio, tagged `theoretical ratio`). The ordinary share's
  premium exists because it carries a vote and the preferred does not — how
  much that vote is worth we do not derive theoretically (it depends on
  takeover probability, ownership concentration and liquidity); we take
  what the market has HISTORICALLY paid for it. Both classes thus have
  zones derived from the same company value: one cannot be "in zone" while
  the other is deep above it, unless today's class ratio deviates from the
  historical median — and then exactly THAT difference is the fact we show.
- **Dividends — payout classification and the sustainable dividend (v3)**:
  every historical payout carries a factual type tag — **regular**;
  **extraordinary** (amount above 150% of the median of that class's prior
  regular payouts); **from retained earnings** (the company's total payout
  above the net profit of the fiscal year it is paid from); the wording of
  the announcement itself (e.g. "extraordinary dividend") takes precedence
  over these rules. The **payout percentage** is computed strictly against
  the profit of the matching fiscal year — if that year is not in the
  database, the field stays empty (never the wrong year). **Expected
  sustainable dividend**: D_sust = sustainable payout × normalized profit
  (trailing 12 months) / share count; the sustainable payout is the
  company's published policy (where it exists and is covered by current
  profit), otherwise the median of historical payout ratios computed ONLY
  over regular payouts — one-offs never enter the base. For banks, payout
  above 80% carries a regulatory-approval note, and at most 70% is used for
  the sustainable base. **Announcement coverage** = normalized profit /
  announced payout; below 1.2 the payout is tagged "tightly covered", below
  1.0 the announcement is not used in the estimate. The dividend discount
  model runs on D_sust — never on the raw last payout.
- **Peers** — the median of actual multiples of comparable ZSE companies in
  the same sector (auto parts are not compared with food); where no sector
  peers exist on the ZSE, the method carries low confidence and does NOT
  anchor the zone. *Planned: European sector medians with size and
  liquidity adjustments.*
- **Discounts are measured, not assumed** — the lesson of Berkshire (trades
  at no discount or a premium) and European holdings (20–40%): the discount
  depends on the company. For Adris we measured its own historical
  price-to-parts relationship — it shows a premium, so we apply no
  discount; an integrated parent like Končar (control + same business) gets
  0–5%; the default 15–25% is used only where measurement is impossible,
  clearly tagged.

## Growth: a sustainability assessment, not a blind cap

The growth rate is the most sensitive input of any valuation. Instead of
cutting every company's growth to the same ceiling, we assess **for each
company whether its growth is STRUCTURALLY SUSTAINABLE** — and explain it on
the page. The inputs are strictly published numbers:

- **Observed growth** = the MEDIAN of annual rates across the whole series of
  annual reports (the median is robust to a single exceptional year, unlike
  CAGR which one base or peak year distorts).
- **Self-funding capacity** = ROE × the retained share of profit — the growth
  a company can fund from its own earnings without new debt or issuance.
- **Order book (backlog)**, when published as a hard figure — corroborates
  higher near-term growth (forward visibility, not an estimate).

**How we judge sustainability.** When observed growth MATCHES self-funding
capacity (e.g. both ~20%), the growth is funded from own earnings and is
deemed structurally sustainable — such a company **may carry growth above
10%** (there is no blind cap). Rising margins over the period further confirm
quality (growth carries profitability, not just volume). When observed growth
SUBSTANTIALLY EXCEEDS self-funding capacity without a published order book,
part of the growth needs external financing or is cyclical — we then anchor to
the fundable rate and say so clearly.

**One-off effects are named and excluded.** If one year stands out (e.g. +31%
vs a median of ~8% — likely an acquisition or one-off revenue), the
representative growth uses the MEDIAN, not the CAGR that year would inflate;
the year is named with an explanation. When growth is decelerating (the last
year well below the median), the near-term rate moves toward the more recent
signal.

**Reversion to the mean.** The estimated near-term rate (g1) fades LINEARLY
over 5 years toward the terminal anchor (~4%, nominal GDP) — no company grows
above-average forever. The only upper limit is a **sanity ceiling of 25%**
(five-year growth above that is implausible), not an arbitrary 10%. Growth
cannot be negative without multi-year evidence of contraction.

**Why one year is not a growth rate**: comparing the last 12 months with the
prior year captures both one-off effects and base effects; it stays as
context, never a standalone source of g1.

## EV and EV/EBITDA — numerator and denominator must cover the same scope

Enterprise value (EV) and EBITDA only make sense if they measure the SAME
business:

- **Minority interests are ADDED to EV.** When a company consolidates a
  subsidiary (control, typically >50%), consolidated EBITDA contains 100%
  of that subsidiary — including the part belonging to the subsidiary's
  other shareholders. The parent's market capitalisation reflects only the
  owners' part, so the minority interest from the balance sheet "buys back"
  the rest, making EV cover the same 100% that EBITDA measures. Without it,
  the multiple is artificially low precisely for companies with large
  consolidated subsidiaries.
- **Short-term financial assets are deducted alongside cash.** Marketable
  securities, short-term deposits and financial assets at fair value are
  de facto cash; the formal "cash and equivalents" line would understate
  liquid assets. The figure carries the `incl. short-term fin. assets`
  badge and the click-through breakdown shows both components separately.
  Long-term financial assets and strategic stakes are NOT deducted — they
  are not cash.
- **Associates (<50%, no control) are excluded from EV.** They are not
  consolidated, so their profit is NOT in EBITDA — consistently, they do
  not enter as minority interest either; instead, the book value of the
  investment (equity method) is DEDUCTED from EV as a separate asset. When
  such an unconsolidated stake is significant, a note accompanies the
  multiple — the multiple is not distorted, but the reader can see that
  part of the company's value lives outside it.
- **Formula**: EV = market capitalisation (all classes) + total debt − cash
  and equivalents − short-term financial assets + minority interests −
  book value of associates. The same principles apply to peer multiples
  (peer EV uses the same formula) and to the bridge from implied EV back to
  per-share value in the peer comparison (− net debt − minority interest +
  short-term financial assets + associates).

### Leverage and ROCE — two numbers because there are two definitions

- **Debt/equity** for us means **only interest-bearing** financial debt
  (loans, bonds, leases) against parent book equity — a measure of real
  financial leverage. Alongside it we show **Liabilities/equity** = **total**
  liabilities (including suppliers, customer advances and provisions) against
  total equity — the classic accounting ratio most portals call
  "debt/equity". For companies with large customer advances on long-cycle
  contracts (e.g. equipment makers) the first ratio can be a few percent while
  the second is ~100% — same company, two true numbers; we show both so the
  definitional difference is obvious.
- **ROCE** (return on capital employed) = EBIT / (total assets − current
  liabilities) — the whole operation in numerator and denominator, comparable
  across differently leveraged companies. Our EBIT does not include the profit
  of associates (equity method), so the figure can be lower than portals that
  include it.

## How we guard against errors

- **Input validations**: the balance sheet must balance, parent profit +
  minorities must equal total profit, EBITDA = EBIT + depreciation — a
  report that fails does not enter the analysis.
- **Parent = sum-of-parts identity**: for holdings, every line (stake ×
  value, cash, debt, discount) must be visible in the table and sum to the
  anchor; an impossible sum = red flag and the analysis is held back.
- **QA flags**: methods that disagree, a wide zone, a large deviation from
  the market — all logged and displayed, never hidden.
- **"What the price implies"**: when our zone is far from the market price,
  we compute the growth or multiple the price implies and compare it with
  **our composite growth** (series / sustainable / terminal) — an implied
  growth within 2 percentage points of the composite we call plausible, a
  larger deviation questionable. It is a comparison of implications, not a
  verdict on the market.
- **Conservatism once**: caution is applied in one place, not stacked in
  layers (e.g. a discount is not added on top of already conservative
  subsidiary estimates).

## Lessons learned — currently effective assumptions

We develop the methodology publicly and iteratively. Instead of a revision
chronology, here are the conclusions those iterations left behind — the
assumptions fair-value zones are computed with TODAY:

- **The fair-value zone is the median of qualified methods, not one
  method's range.** The single-anchor dogma proved brittle: confirmations
  converging elsewhere must influence the zone, and an anchor change must
  not flip a stock from "above" to "below" overnight. The anchor still
  shapes the sensitivity; an anchor whose own range exceeds 100% of its
  base loses primacy (visibly, with a reason).
- **Growth is derived exclusively from published numbers, as a
  composite.** The historical average alone is a poor forecaster, manual
  forward estimates are invention, and a single year-on-year comparison
  measures one-off and base effects — hence g1 is the median of three
  signals (multi-year series, sustainable growth from retained earnings,
  terminal anchor), capped from above and always below the cost of equity.
- **Every risk is charged exactly once.** The cost of equity is a visible
  breakdown: rf (German Bund) + β×ERP (mature market) + CRP (a small,
  separate Croatian premium) + an illiquidity premium only below the
  liquidity threshold; betas of illiquid series never enter raw (sector
  betas, bounds). Conservatism is likewise applied once, not in layers.
- **Dividends: we compute on the SUSTAINABLE dividend, and the hardest
  evidence enters the estimate.** Payouts are classified
  (regular/extraordinary/from retained earnings); one-offs never enter the
  base. When the Gordon value of the sustainable dividend exceeds the
  zone's lower bound, it ENTERS the zone (the dividend floor) — the
  estimate is not suspended, because the reader would be left without
  information exactly where the evidence is firmest.
- **Freshness before audit, with strict gates.** Where quarterly data
  exist, earnings/revenue/ROE are computed on the trailing 12 months (TTM)
  with consistency checks; where they do not, an `annual data` tag stands.
  Better an empty field with a reason than a wrong number.
- **Every share class has its own zone.** Company value is apportioned to
  classes by the market price ratio — one zone for two classes told two
  stories about the same company.
- **Parents: the parts are valued from the right sources.** The standalone
  business exclusively from separate statements (never approximated from
  consolidated ones), joint ventures at book value from the notes,
  recomputation in dependency order (subsidiaries before parents).
- **The distribution versus the market is a diagnostic, never a
  calibration target.** When too many liquid names end up on the same side
  of their zones, an automatic alarm demands a review of OUR inputs — zones
  are reviewed, not fitted to prices.

- **A parent's consolidated DCF with listed subsidiaries ≠ SOTP — and why
  (July 2026).** When a parent consolidates subsidiaries (KONČAR: KODT, DLKV),
  the consolidated DCF discounts 100% of their cash flows. Two consequences:
  (1) the minority interest must be removed PROPORTIONALLY (minorities hold a
  share of the growing stream, not of static book value — the earlier static
  book-NCI deduction understated minorities, e.g. KOEI €156m static vs ~€800m
  proportional; fixed); (2) even then the consolidated DCF grows others'
  (already market-priced) subsidiaries at the group rate and values them above
  their market price — so it STRUCTURALLY exceeds SOTP. For such parents the
  anchor is SOTP (each subsidiary at market, ownership share respected), and
  the consolidated DCF stays context with a clear caveat.
- **EV must contain minority interests — an acknowledged error (July
  2026).** External expert feedback confirmed an inconsistency: the
  displayed indicators did add minority interests to EV, but the bridge
  from peer multiples back to per-share value and the peer EV used in
  calibration did NOT — overvaluing companies with large minority
  interests (multiple × 100% of EBITDA, with only net debt deducted).
  Fixed everywhere with a single formula; associates (equity method) are
  consistently excluded, with a visible note where significant.

We are not infallible now either — which is why every stock has a visible
history of its zone changes with reasons, and we continuously measure the
distribution of our zones against the market.

## Bonds

For bonds we compute no fair-value zone — the display is a **deterministic
yield analysis** from public inputs (clean price from the ZSE, coupon and
maturity from the listing data). There are no growth or discount-rate
assumptions; every number follows from a formula:

- **Prices are clean**, in % of par — as quoted on the ZSE. Bonds trade
  rarely, so the price is often stale: such a price carries an ILLIQ. tag
  and is indicative, as with stocks.
- **Current yield** = annual coupon / clean price.
- **Accrued interest** (ACT/ACT ICMA): coupon/frequency × days since the
  last coupon / days in the coupon period. The day-count convention and
  coupon frequency live in the prospectus — until we confirm them from the
  prospectus, we use ACT/ACT and an annual coupon and TAG that as an
  assumption.
- **YTM (yield to maturity)**: the rate y at which the dirty price (clean +
  accrued interest) equals the sum of discounted future payments:
  Σ CF/(1+y)^t, where t are times to payment in years (ACT/365.25) and the
  payment schedule is derived backwards from maturity. We solve by
  bisection (deterministic, no local minima); the settlement date for the
  calculation is the date of the last price.
- **Duration**: Macaulay = Σ t·PV(CF)/Σ PV(CF); modified = Macaulay /
  (1+y). A measure of price sensitivity to yield changes.
- Issuers without a deterministic name source carry the status **"master
  data in progress"** — nothing is invented; YTM is not shown without
  complete inputs (coupon + maturity + price).

## Where the data comes from

A summary of sources — every data type on the site has a known origin and a
declared freshness (verified 15 July 2026):

- **Prices**: the official ZSE price list (end-of-day JSON); updated on
  business days after the close of trading (16:00 CET), and every price
  carries the actual data date. Per-security history from the ZSE archive.
  Illiquid stocks carry a tag next to the price.
- **Financial reports**: the EHO register of regulated information
  (issuers' official filings, PDF/XLSX). Standardized forms (TFI-POD, the
  banks' supervisory form, FINREP, insurers' ISD) are read by deterministic
  parsers that verify the AOP code and row label; whatever fails validation
  does not enter the analysis. Every number carries a document and page.
- **Dividends**: the ZSE security page (amount, ex-date, record date,
  payment) + official proposal announcements. A proposal is not a payment —
  the status is always visible.
- **Share count / ISIN**: the ZSE security page (listed quantity, classes);
  treasury shares from annual-report notes.
- **Shareholders (top 10)**: the ZSE security page (source SKDD; the list
  has no published as-of date — we track it by fetch date) + largest-
  shareholder tables from annual reports (with a page citation). Custodian
  and omnibus accounts are tagged — they are not ultimate beneficial
  owners. Changes are shown only when two snapshots exist; names strictly
  as published.
- **Risk-free rate and risk premium**: the yield of the Croatian 10-year
  government bond + Damodaran's premium for Croatia; manually calibrated
  with a citation in every valuation, revised at each recalibration.
- **Peer multiples**: computed from our own database (ZSE companies with
  validated financials), peer-set criteria publicly documented; a sector
  without a comparable peer gets no peer method.

The detailed source register (how each source is read, its known
weaknesses, verification dates) is maintained in internal project
documentation and revised regularly.

## Frequently asked questions

**What is the fair-value zone?** A per-stock value range produced by our
valuation methods (the anchor method for the company's archetype ±
sensitivity to key assumptions). It is not a target price — it is a factual
display of what the fundamentals say under publicly stated assumptions.

**How is the fair-value zone computed?** Each company gets an archetype
(bank, industrial, holding…) which determines the anchor method (e.g.
residual income for banks, DCF for operating companies, SOTP for holdings).
Zone = anchor ± sensitivity to the key assumption; the other methods serve
as confirmation. All parameters (cost of equity, growth, peer multiples)
carry a cited source on the stock page itself.

**Are these buy or sell recommendations?** No. The service publishes no
recommendations, ratings or target prices. A price above or below the zone
is a fact from the data, not a signal — the conclusion is always the
reader's. For investment decisions, consult a licensed adviser.

**Why does a stock have no fair-value zone?** A zone is published only when
the data passes validation. If reports are missing or fail the checks, we
show only the market profile — fields stay empty (n/a), nothing is
estimated.

**How fresh is the data?** Prices are official Zagreb Stock Exchange
end-of-day closes; they update on business days after the close of trading
(16:00 CET), and every price carries the actual data date. Financials
update when the issuer publishes a report (EHO register). A date stands
next to every number.

## Automation

The analyses are generated by an automated system under human oversight:
data comes from official sources (ZSE, the EHO register of filings), every
number carries a source (document + page), and reports that fail validation
stay out of the analysis until we review them. The system writes no
recommendations — by design.
