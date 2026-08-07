/**
 * Investor-facing help copy for Thesis table columns and drawer values.
 * Tone: plain English for a new investor — what / how / why.
 */

export interface ThesisHelpEntry {
  /** Short heading shown in the tip. */
  title: string;
  /** What this number or label means. */
  what: string;
  /** How FolioTracker computes or sources it. */
  how: string;
  /** Why a long-term investor should care. */
  why: string;
}

function help(
  title: string,
  what: string,
  how: string,
  why: string,
): ThesisHelpEntry {
  return { title, what, how, why };
}

/** Table column headers. */
export const TABLE_COLUMN_HELP: Record<string, ThesisHelpEntry> = {
  ticker: help(
    "Ticker",
    "The stock’s trading symbol and company name.",
    "Taken from your Held / Watched lists on the Watchlist page.",
    "This is the company you are evaluating — click the row for the full thesis.",
  ),
  list: help(
    "List",
    "Whether you mark this name as Held (you own it) or Watched (on your radar).",
    "Set when you add the ticker on Watchlist.",
    "Held names usually deserve more attention because your capital is at risk.",
  ),
  data: help(
    "Data coverage",
    "How complete the fundamentals were for this Generate run: ok, partial, or thin.",
    "Based on whether framework scores, valuation, and sources came back. Rate limits can leave a row thin.",
    "Thin rows stay honest blanks — don’t treat missing scores as a sell signal.",
  ),
  sector: help(
    "Sector",
    "The industry group the company belongs to (when the data source provides it).",
    "Pulled from fundamentals providers such as Yahoo Finance.",
    "Sectors help you compare like with like and spot concentration risk.",
  ),
  graham: help(
    "Graham Deep Value",
    "A 0–100 score inspired by Benjamin Graham’s deep-value checklist.",
    "Weighted checks such as Margin of Safety, Current Ratio, Debt, and Earnings Stability. Score needs ≥ 50% of check weight available.",
    "High scores suggest a cheaper, more defensive bargain — not a growth story.",
  ),
  financial_strength: help(
    "Financial Strength",
    "A 0–100 score of balance-sheet and cash-flow health.",
    "Weighted checks for Liquidity, Leverage, Net cash, Free cash flow, Operating cash flow, Profitability, and ROE.",
    "Strong finances help a company survive downturns and fund its own growth.",
  ),
  os: help(
    "Investment OS Score",
    "A composite 0–100 “operating system” score across quality, valuation, and thesis stability.",
    "Weighted blend of eight dimensions (business quality, financial strength, valuation, balance sheet, and more). Needs enough coverage to publish.",
    "Use it as a portfolio glance — not a buy button. Drill into dimensions in the drawer.",
  ),
};

/** Drawer section / field help. */
export const DRAWER_HELP: Record<string, ThesisHelpEntry> = {
  frameworks_section: help(
    "Investment frameworks",
    "Each philosophy grades the same company with different questions.",
    "Graham emphasizes bargain price and safety; Financial Strength emphasizes balance sheet and cash flow. Scores are weighted means of named checks.",
    "Seeing both lenses reduces the chance you buy a “cheap” company that is financially fragile.",
  ),
  framework_score: help(
    "Framework score",
    "Overall 0–100 grade for this philosophy.",
    "Weighted average of check points when enough check weight (≥ 50) is computable; otherwise shown as —.",
    "Compare across holdings — a 90 vs a 40 is a big difference in how the checklist sees the stock.",
  ),
  framework_check: help(
    "Framework check",
    "One yes/no or graded test inside the philosophy (for example Current Ratio or ROE).",
    "Uses fundamentals from Yahoo / SEC / Alpha Vantage when available. Missing inputs stay — — never invented.",
    "The detail line shows the threshold used so you can re-check the math yourself.",
  ),
  os_score: help(
    "Investment OS Score",
    "Composite health score for this ticker across eight research dimensions.",
    "Each dimension gets 0–100 points and a locked weight (they sum to 100). Score needs coverage ≥ 50.",
    "Helps you rank names when you don’t have time to read every checklist line.",
  ),
  os_dimension: help(
    "OS dimension",
    "One slice of the Investment OS Score (quality, valuation, balance sheet, etc.).",
    "Derived from framework checks, Margin of Safety, FCF yield, and thesis verdicts where available.",
    "If one dimension is weak, open that engine below — don’t average away a real risk.",
  ),
  valuation_section: help(
    "Valuation",
    "Answers “Am I paying too much?” with several estimates at once.",
    "Builds Graham-, Buffett-, and modern-style methods from the same fundamentals, then a six-rung ladder.",
    "Price alone is not expensive or cheap — compare it to independent estimates of worth.",
  ),
  margin_of_safety: help(
    "Margin of Safety",
    "How far market price sits below (or above) estimated intrinsic value.",
    "(Intrinsic − Price) / Intrinsic. Stars and a rating summarize the cushion.",
    "Graham’s idea: buy with a cushion so mistakes and bad luck hurt less.",
  ),
  intrinsic_value: help(
    "Intrinsic value",
    "An estimate of what the business is worth based on fundamentals — not today’s quote.",
    "Taken from valuation methods (often Graham intrinsic / fair-value median). Shown as — when inputs are missing.",
    "Your job is to decide if the estimate is reasonable, then compare it to price.",
  ),
  market_price: help(
    "Market price",
    "What investors are paying for the stock right now (per share when available).",
    "From the latest fundamentals snapshot used in Generate.",
    "Useful only next to an estimate of worth — alone it doesn’t tell you if the stock is a deal.",
  ),
  mos_stars: help(
    "Margin of Safety stars",
    "A 1–5 star shorthand for how large the safety cushion is.",
    "Mapped from the Margin of Safety percentage bands used in the Valuation Engine.",
    "More stars = more cushion under the estimate — still not a guarantee.",
  ),
  valuation_ladder: help(
    "Valuation ladder",
    "Several “rungs” of firm value stacked for quick comparison.",
    "Market, intrinsic, liquidation, replacement (often unavailable), enterprise, and expected fair (median of key methods).",
    "If market sits well above intrinsic and fair value, you may be paying a premium.",
  ),
  ladder_market: help(
    "Market price (ladder)",
    "Current market value on the ladder.",
    "Same market price input used elsewhere in valuation.",
    "The reference point for every other rung.",
  ),
  ladder_intrinsic: help(
    "Intrinsic value (ladder)",
    "Estimated economic worth of the equity.",
    "From Graham-style intrinsic methods when inputs exist.",
    "Buying below this leaves a margin of safety.",
  ),
  ladder_liquidation: help(
    "Liquidation value",
    "Rough estimate of what assets might fetch if the company were wound down.",
    "Conservative asset haircuts minus liabilities when balance-sheet data exists.",
    "A floor-style number — useful for deep-value, not for growth compounders.",
  ),
  ladder_replacement: help(
    "Replacement value",
    "What it might cost to rebuild the business from scratch.",
    "Not yet locked in FolioTracker — shown as — until a method ships.",
    "When available, it helps spot capital-intensive businesses priced below rebuild cost.",
  ),
  ladder_enterprise: help(
    "Enterprise value",
    "Value of the whole firm to equity and debt holders (market-based).",
    "Typically equity market value plus net debt when those inputs exist.",
    "Useful for comparing companies with different debt levels.",
  ),
  ladder_expected_fair: help(
    "Expected fair value",
    "A middle-of-the-road fair value from several methods.",
    "Median of available Intrinsic / DCF / Adjusted book estimates.",
    "A single number to compare against market when methods disagree.",
  ),
  valuation_method: help(
    "Valuation method",
    "One specific way to estimate value (NCAV, FCF yield, DCF, EV/EBITDA, etc.).",
    "Each school (Graham / Buffett / Modern) uses its own formulas on the same fundamentals. Detail notes inputs and assumptions.",
    "Disagreement across methods is information — dig into why, don’t average blindly.",
  ),
  net_assets: help(
    "Net Asset Intelligence",
    "Compares the market’s price for the company to its adjusted net assets.",
    "Assets minus liabilities → adjusted net assets, then difference % vs market cap, with an honest verdict.",
    "Helps spot cases where the quote looks disconnected from book-like asset value.",
  ),
  adjusted_net_assets: help(
    "Adjusted net assets",
    "Assets minus liabilities after available adjustments.",
    "Built from the asset and liability lines shown above; missing lines stay blank.",
    "If market cap is far below this, the market may be pricing in trouble — or opportunity.",
  ),
  asset_difference: help(
    "Asset difference %",
    "How far market cap sits from adjusted net assets.",
    "(Adjusted net assets − market cap) / market cap style difference, with a verdict label.",
    "Large gaps deserve a reason: write-downs, off-balance items, or mispricing.",
  ),
  monitoring_section: help(
    "Thesis monitoring",
    "Tracks whether your investment story is getting stronger or weaker — not just the stock price.",
    "Compares today’s signal vector to a baseline snapshot. Verdicts are a closed set: No change, Strengthened, Slightly weaker, Broken.",
    "Price can bounce while the thesis quietly breaks — this surface watches the story.",
  ),
  thesis_verdict: help(
    "Thesis verdict",
    "A closed-set label for how the thesis changed since the baseline.",
    "Deterministic rules on score/MoS deltas (with optional narrative mode). Never free-prose ratings.",
    "Broken or Slightly weaker means re-read your reasons for owning — don’t ignore it.",
  ),
  advisor_section: help(
    "AI Portfolio Advisor",
    "The only place FolioTracker may say buy more / hold / trim / research / wait.",
    "Deterministic rules over frameworks, valuation, and monitoring; optional LLM mode stays fail-closed. Always shows reasoning, confidence, and provider.",
    "Treat it as a second opinion with receipts — not an order ticket.",
  ),
  advisor_conclusion: help(
    "Advisor conclusion",
    "Suggested posture: buy more, hold, trim, research further, or wait.",
    "Mapped from MoS, framework scores, and thesis verdicts with an explicit confidence and provider label.",
    "Always read the reasoning lines — the verb alone is not enough.",
  ),
  coverage_badge: help(
    "Data coverage",
    "Honesty label for how much of this ticker’s thesis could be computed.",
    "ok = broad coverage; partial = some engines filled; thin = mostly blanks (often rate limits).",
    "Thin data means “we don’t know yet,” not “the stock is bad.”",
  ),
};

/** Lookup by framework check name (exact match from backend). */
export const CHECK_HELP: Record<string, ThesisHelpEntry> = {
  "Margin of Safety": help(
    "Margin of Safety (Graham)",
    "Is the stock trading below estimated intrinsic value with a cushion?",
    "Compares price to Graham-style intrinsic estimate; grades the percentage cushion.",
    "Buying with a cushion is Graham’s main defense against being wrong.",
  ),
  "Net-Net (cash proxy)": help(
    "Net-Net",
    "Is the stock cheaper than a conservative reading of net current assets?",
    "Cash-proxy net-net check from current assets / liabilities style inputs when available.",
    "Classic deep-value screen — rare today, powerful when it appears.",
  ),
  "Current Ratio": help(
    "Current Ratio (Graham)",
    "Can short-term assets cover short-term bills?",
    "Current assets ÷ current liabilities; Graham wants a healthy surplus (spec minimum applied).",
    "Low ratios can mean liquidity stress even if the stock looks “cheap.”",
  ),
  Debt: help(
    "Debt (Graham)",
    "Is leverage modest enough for a defensive investor?",
    "Uses debt-to-equity style inputs with Graham-oriented thresholds.",
    "High debt turns a bargain into a riskier bet in a downturn.",
  ),
  "Earnings Stability": help(
    "Earnings Stability",
    "Have earnings been consistently positive rather than a one-year fluke?",
    "Looks for sustained profitability signals in available earnings history fields.",
    "Stable earners are easier to value; volatile earners need a bigger discount.",
  ),
  "Dividend History": help(
    "Dividend History",
    "Does the company have a reliable dividend track record?",
    "Currently often unavailable in sources — shown as — rather than guessed.",
    "Dividends can mark shareholder-friendly cash return, but absence isn’t automatically bad.",
  ),
  Liquidity: help(
    "Liquidity (Financial Strength)",
    "Short-term ability to pay bills (current ratio lens).",
    "Current ratio vs Financial Strength minimum threshold.",
    "Liquidity buys time when revenue dips.",
  ),
  Leverage: help(
    "Leverage",
    "How much debt the company carries relative to equity.",
    "Debt-to-equity style check with graded points.",
    "Extra leverage amplifies both gains and losses.",
  ),
  "Net cash position": help(
    "Net cash position",
    "Whether cash exceeds debt (a fortress balance sheet signal).",
    "Cash and equivalents vs total debt when both exist.",
    "Net cash firms have optionality — they can invest or weather storms.",
  ),
  "Free cash flow": help(
    "Free cash flow",
    "Cash left after running the business and maintaining it.",
    "Positive/negative FCF check from cash-flow statement fields.",
    "FCF funds dividends, buybacks, and debt paydown without new borrowing.",
  ),
  "Operating cash flow": help(
    "Operating cash flow",
    "Cash generated by core operations.",
    "Requires operating cash flow > 0 when the field exists.",
    "Earnings without cash can be a warning sign.",
  ),
  Profitability: help(
    "Profitability",
    "Is the company making money on sales / net income?",
    "Uses profit margin or positive net income when margin is missing.",
    "Unprofitable businesses need a growth story — and more skepticism.",
  ),
  "Return on equity": help(
    "Return on equity (ROE)",
    "How much profit the company earns on shareholders’ equity.",
    "ROE bands (e.g. ≥15% excellent, ≥10% acceptable) → points.",
    "High ROE with modest leverage can signal a quality compounder.",
  ),
};

/** OS dimension help by id. */
export const OS_DIMENSION_HELP: Record<string, ThesisHelpEntry> = {
  business_quality: help(
    "Business Quality",
    "How good the underlying business looks on profitability and ROE.",
    "Average of Financial Strength Profitability and ROE check points.",
    "Quality businesses can justify higher prices — still check valuation.",
  ),
  financial_strength: help(
    "Financial Strength (OS)",
    "Overall Financial Strength framework score as an OS dimension.",
    "Uses the FS 0–100 score when coverage allows.",
    "Weak finances can invalidate an otherwise “cheap” thesis.",
  ),
  valuation: help(
    "Valuation (OS)",
    "How attractive the price looks versus intrinsic value.",
    "Maps Margin of Safety into 0–100 points (full points near ~50% MoS).",
    "Even great businesses can be poor investments at the wrong price.",
  ),
  balance_sheet: help(
    "Balance Sheet (OS)",
    "Liquidity, leverage, and net-cash health.",
    "Average of Liquidity, Leverage, and Net cash check points.",
    "Balance-sheet strength is your ballast in recessions.",
  ),
  earnings_quality: help(
    "Earnings Quality",
    "Whether earnings look durable and cash-backed.",
    "Combines Earnings Stability (Graham) and Operating cash flow (FS).",
    "Soft earnings quality means the intrinsic value estimate is shakier.",
  ),
  capital_allocation: help(
    "Capital Allocation",
    "How effectively the firm turns capital into cash for owners.",
    "Prefers FCF yield (Buffett school); falls back to Free cash flow check.",
    "Good allocators compound; poor ones destroy value even with growth.",
  ),
  framework_consensus: help(
    "Framework Consensus",
    "Do Graham and Financial Strength roughly agree?",
    "100 minus a penalty for the gap between the two scores (both required).",
    "Big disagreements mean dig deeper before sizing a position.",
  ),
  thesis_stability: help(
    "Thesis Stability",
    "Has the investment story held up since your baseline?",
    "Maps thesis verdict: Strengthened 100 → Broken 0.",
    "A weakening thesis is a reason to re-underwrite, not average down blindly.",
  ),
};

/** Valuation method help by method id. */
export const METHOD_HELP: Record<string, ThesisHelpEntry> = {
  ncav: help(
    "NCAV (cash proxy)",
    "Net current asset value — a Graham-style floor on working capital.",
    "Current assets (cash-proxy) minus liabilities, compared to market.",
    "Deep-value screen for extreme bargains.",
  ),
  net_net: help(
    "Net-Net",
    "Stricter Graham test: price below a haircut of net current assets.",
    "Flags whether the stock clears the net-net undervaluation bar.",
    "Rare setups; historically associated with high expected returns and high risk.",
  ),
  intrinsic: help(
    "Intrinsic Value (Graham)",
    "Graham-inspired estimate of equity worth.",
    "Uses available earnings / book style inputs per the Valuation Engine.",
    "Anchor for Margin of Safety.",
  ),
  liquidation: help(
    "Liquidation Value",
    "Conservative wind-down value of the assets.",
    "Haircut assets minus liabilities when the balance sheet is complete enough.",
    "A downside reference, not a going-concern target price.",
  ),
  adjusted_book: help(
    "Adjusted Book Value",
    "Book equity after available adjustments.",
    "Asset/liability based book estimate from fundamentals.",
    "Useful when earnings power is hard to trust but assets are tangible.",
  ),
  margin_of_safety: help(
    "Margin of Safety (method)",
    "Cushion between intrinsic estimate and price.",
    "Same MoS idea surfaced as a Graham-school method row.",
    "Larger cushions leave room for error.",
  ),
  owner_earnings: help(
    "Owner Earnings",
    "Buffett-style cash earnings available to owners.",
    "Approximated from free-cash / owner-earnings proxies in fundamentals.",
    "Closer to what a private owner could take out than accounting net income.",
  ),
  fcf_yield: help(
    "FCF Yield",
    "Free cash flow as a percentage of market value.",
    "FCF ÷ market cap (or price proxy) when both exist.",
    "Higher yields can mean you’re paid well to wait — check if FCF is sustainable.",
  ),
  roic: help(
    "ROIC",
    "Return on invested capital.",
    "Often unavailable in current sources — shown as — rather than invented.",
    "Great businesses earn high returns on the capital they use.",
  ),
  capital_efficiency: help(
    "Capital Efficiency",
    "How well the firm converts capital into cash returns.",
    "Buffett-school efficiency proxy from available cash-flow / capital fields.",
    "Inefficient capital use can cap long-term compounding.",
  ),
  dcf: help(
    "DCF (Gordon)",
    "Simple discounted cash-flow value assuming perpetual growth.",
    "Gordon growth model with conservative defaults (e.g. discount ~10%, growth capped).",
    "Sensitive to growth assumptions — treat as a scenario, not gospel.",
  ),
  reverse_dcf: help(
    "Reverse DCF",
    "What growth the market price already implies.",
    "Backs out implied growth from today’s price and cash-flow inputs.",
    "If implied growth looks heroic, the stock may be priced for perfection.",
  ),
  ev_ebitda: help(
    "EV/EBITDA",
    "Enterprise value versus operating earnings before non-cash charges.",
    "EV ÷ EBITDA when both are present.",
    "Common relative-value multiple — compare within an industry.",
  ),
  peg: help(
    "PEG",
    "Price/earnings relative to growth.",
    "PE ÷ growth rate style multiple when inputs exist.",
    "Can flag whether you’re overpaying for growth — still check growth quality.",
  ),
};

export function helpForCheck(name: string): ThesisHelpEntry {
  return (
    CHECK_HELP[name] ??
    help(
      name,
      "A named checklist item inside an investment framework.",
      "Computed from available fundamentals; — means inputs were missing.",
      "Read the detail line for the exact threshold used on this run.",
    )
  );
}

export function helpForOsDimension(id: string): ThesisHelpEntry {
  return (
    OS_DIMENSION_HELP[id] ??
    DRAWER_HELP.os_dimension
  );
}

export function helpForMethod(id: string, label: string): ThesisHelpEntry {
  return (
    METHOD_HELP[id] ??
    help(
      label,
      "One valuation estimate from a named method.",
      "Uses fundamentals when present; otherwise —.",
      "Compare several methods before trusting any single number.",
    )
  );
}

export function helpForLadderRung(
  key: keyof typeof TABLE_COLUMN_HELP | string,
): ThesisHelpEntry {
  const map: Record<string, string> = {
    market: "ladder_market",
    intrinsic: "ladder_intrinsic",
    liquidation: "ladder_liquidation",
    replacement: "ladder_replacement",
    enterprise: "ladder_enterprise",
    expected_fair: "ladder_expected_fair",
  };
  return DRAWER_HELP[map[key] ?? "valuation_ladder"];
}
