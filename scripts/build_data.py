"""
ZENITH SCANNER PRO — Build Data Pipeline v14.0
Dual data sources: Yahoo Finance (primary) + Finnhub (secondary).
Run: python scripts/build_data.py --out-dir data
"""
import argparse, json, os, time, warnings
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
try:
    import urllib.request
    HAS_URLLIB = True
except:
    HAS_URLLIB = False

warnings.filterwarnings("ignore")

FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")  # Free key from finnhub.io

def finnhub_quote(ticker):
    """Get real-time quote from Finnhub (free tier: 60 calls/min)."""
    if not FINNHUB_KEY or not HAS_URLLIB:
        return None
    try:
        t = ticker.replace(".HK", "")  # Finnhub uses different format for HK
        url = f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_KEY}"
        req = urllib.request.Request(url, headers={"User-Agent": "NexusScannerPro/8.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        if data and data.get("c", 0) > 0:
            return {"close": data["c"], "high": data["h"], "low": data["l"],
                    "open": data["o"], "prev_close": data["pc"], "change_pct": data.get("dp", 0)}
    except:
        pass
    return None

def finnhub_metrics(ticker):
    """Get basic financials from Finnhub."""
    if not FINNHUB_KEY or not HAS_URLLIB:
        return {}
    try:
        t = ticker.replace(".HK", "")
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={FINNHUB_KEY}"
        req = urllib.request.Request(url, headers={"User-Agent": "NexusScannerPro/8.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        m = data.get("metric", {})
        return {
            "pe_finnhub": m.get("peBasicExclExtraTTM"),
            "roe_finnhub": m.get("roeTTM"),
            "roa_finnhub": m.get("roaTTM"),
            "eps_growth_finnhub": m.get("epsGrowthTTMYoy"),
            "beta": m.get("beta"),
            "52w_high": m.get("52WeekHigh"),
            "52w_low": m.get("52WeekLow"),
            "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
        }
    except:
        return {}

warnings.filterwarnings("ignore")

# ── TICKER UNIVERSE ──────────────────────────────────────────────
GROUPS = {
    # ── US CORE ──
    "🎯 Watchlist Core": [
        "VRT","POWL","ETN","ANET","MPWR","PWR","CAT","FCX",
        "NVDA","PLTR","AVGO","AMD","LMT","NOC","CEG","SMCI",
        "GE","ROK","URI","DE"
    ],
    "🤖 AI & Semiconductors": [
        "TSM","ASML","LRCX","KLAC","MU","ARM","ON",
        "QCOM","AMAT","MRVL","ADI","NXPI"
    ],
    # ── LATAM COMPLETO ──
    "🌎 LATAM": [
        "NU","MELI","VALE","PBR","SQM","BSBR","ABEV","ITUB",
        "GLOB","STNE","AMX","FMX","PAC","VIST","SUPV",
        "BAP","KOF","BMA","IFS","TGLS","YPF","BCH","BVN",
        "BSAC","EDN","BWMX","BBAR","DLO","CCU","TEO",
        "CX","AUNA","TV"
    ],
    # ── COLOMBIA ──
    "🇨🇴 Colombia": [
        "EC","CIB","AVAL","CNNE","CRGIY"
    ],
    # ── ESPAÑA ──
    "🇪🇸 España": [
        "SAN","TEF","BBVA","IBE","ITX","REP"
    ],
    # ── REINO UNIDO ──
    "🇬🇧 Reino Unido": [
        "SHEL","AZN","HSBC","BP","RIO","LSEG",
        "GSK","UL","DEO","BCS","NWG","VOD"
    ],
    # ── CHINA CONTINENTAL ──
    "🇨🇳 China Continental": [
        "BABA","PDD","JD","BIDU","NIO","LI",
        "XPEV","ZK","FUTU","TME","BILI","YMM"
    ],
    # ── HONG KONG ──
    "🇭🇰 Hong Kong": [
        "0700.HK","9988.HK","1299.HK","0005.HK","2318.HK",
        "0388.HK","0941.HK","1810.HK","9618.HK","3690.HK"
    ],
    # ── ÍNDICES MUNDIALES ──
    "📊 Índices Mundiales": [
        "SPY","QQQ","DIA","IWM",
        "EWZ","EWW","FXI","MCHI",
        "EWU","EWG","EWQ","EWJ","EWY",
        "EWA","EZA","EWT"
    ],
    # ── ETFs GLOBALES ──
    "💼 ETFs Globales": [
        "VTI","VXUS","VWO","VEA",
        "GLD","SLV","USO",
        "XLE","XLF","XLK","XLV","XLI",
        "SOXX","KWEB","ARKK",
        "TLT","HYG","LQD"
    ],
    # ── US MARKET (Top ~350 S&P 500 stocks) ──
    "🇺🇸 US Market": [
        # Tech
        "AAPL","MSFT","GOOGL","AMZN","META","TSLA","ORCL","CRM","ADBE","NOW",
        "PANW","CRWD","SNOW","NET","DDOG","INTU","CDNS","SNPS","FTNT","ZS",
        "WDAY","TEAM","HUBS","DOCU","VEEV","ANSS","CPAY","IT","KEYS","TYL",
        "EPAM","PAYC","MANH","MPWR","NXPI","MCHP","SWKS","QRVO","ZBRA","TER",
        "TRMB","GDDY","GEN","CTSH","WIT","ACN","IBM","CSCO","HPQ","HPE","DELL",
        # Financials
        "JPM","V","MA","GS","MS","BLK","SCHW","AXP","C","BAC","WFC","USB",
        "PNC","TFC","COF","ICE","CME","SPGI","MCO","MSCI","FIS","FISV","GPN",
        "AIG","MET","PRU","AFL","ALL","TRV","CB","AON","MMC","AJG","CINF","BRO",
        # Healthcare
        "UNH","LLY","JNJ","ABBV","MRK","PFE","TMO","ISRG","VRTX","REGN",
        "AMGN","GILD","MDT","SYK","BSX","EW","ZBH","BAX","BDX","HOLX","DXCM",
        "IDXX","MTD","A","WAT","IQV","CRL","TECH","ALGN","PODD","INCY",
        # Energy
        "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","HES",
        "OXY","DVN","HAL","FANG","CTRA","APA","TRGP","WMB","OKE","KMI",
        # Defense & Aerospace
        "RTX","GD","BA","LHX","NOC","LMT","HII","TXT","HWM","TDG","AXON",
        # Industrials
        "HON","MMM","CMI","PH","ITW","TT","EMR","GE","ETN","ROK","AME",
        "DOV","FTV","XYL","NDSN","ROP","IEX","GWW","FAST","WSO","AOS",
        "IR","CARR","OTIS","JCI","GNRC","HUBB","RBC","SNA","WCC",
        # Consumer Discretionary
        "COST","WMT","HD","LOW","NKE","SBUX","MCD","TJX","ROST","DG","DLTR",
        "BKNG","ABNB","MAR","HLT","RCL","CCL","LVS","WYNN","MGM",
        "F","GM","APTV","BWA","LEA","RL","TPR","GRMN","POOL","BBY","TSCO",
        "ORLY","AZO","AAP","KMX","LULU","DECK","ON","ULTA","EL","CPRI",
        # Consumer Staples
        "PG","KO","PEP","PM","MO","STZ","BF.B","MNST","KDP","CLX",
        "CL","KMB","CHD","SJM","HSY","MKC","GIS","CAG","K","HRL","TSN","MDLZ",
        # Real Estate
        "AMT","PLD","CCI","EQIX","PSA","SPG","O","DLR","VICI","WELL",
        "AVB","EQR","MAA","ESS","UDR","ARE","BXP","SLG","VNO",
        # Utilities
        "NEE","DUK","SO","D","AEP","SRE","EXC","XEL","WEC","ES",
        "AEE","CMS","CNP","PNW","NI","EVRG","ATO","PEG",
        # Materials
        "LIN","APD","SHW","ECL","NUE","STLD","CF","MOS","ALB","FMC",
        "IFF","CE","PPG","VMC","MLM","NEM","FCX","AA",
        # Communication Services
        "GOOG","DIS","NFLX","CMCSA","T","VZ","TMUS","CHTR","EA","TTWO",
        "MTCH","ZG","PINS","SNAP","ROKU","SPOT","WBD","PARA","LYV","IACI",
    ],
}

# ── TECHNICAL MODEL (faithful Pine translation) ─────────────────
def compute_score(df):
    """Compute technical score 0-100. Anti-repaint: uses closed candles only."""
    c, h, v = df["Close"], df["High"], df["Volume"]
    ema50 = c.ewm(span=50, adjust=False).mean()
    ema200 = c.ewm(span=200, adjust=False).mean()
    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    # ADX
    tr = pd.concat([h - df["Low"], (h - c.shift()).abs(), (df["Low"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    up = h.diff(); dn = -df["Low"].diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0), index=df.index)
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0), index=df.index)
    pdi = 100 * pdm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr.replace(0, np.nan)
    ndi = 100 * ndm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    # Bollinger
    bb_basis = c.rolling(20).mean()
    bb_dev = c.rolling(20).std() * 2
    bb_w = (bb_basis + bb_dev - (bb_basis - bb_dev)) / bb_basis
    bb_w_low = bb_w.rolling(50).min()
    # Volume
    vol_ma = v.rolling(20).mean()
    rel_vol = v / vol_ma.replace(0, np.nan)
    # OBV
    obv = (np.sign(c.diff()) * v).cumsum()
    obv_sma = obv.rolling(10).mean()
    # Highest
    h20 = h.rolling(20).max()
    # Score components
    s_trend = ((ema50 > ema200) & (c > ema200)).astype(int) * 30
    s_mom = ((rsi > 50) & (rsi < 70)).astype(int) * 15
    s_adx = ((adx > 18) & (adx < 35)).astype(int) * 15
    s_comp = (bb_w < bb_w_low * 1.2).astype(int) * 15
    s_accum = ((obv > obv_sma) & (rel_vol > 1)).astype(int) * 15
    s_brk = (c > h20 * 0.97).astype(int) * 10
    score = s_trend + s_mom + s_adx + s_comp + s_accum + s_brk
    ext = (c - ema50) / ema50 * 100
    # AI probability (sigmoid)
    mz = (rsi - 50) / 10
    ts = (ema50 - ema200) / ema200.replace(0, np.nan)
    vr = bb_w / bb_w.rolling(50).mean().replace(0, np.nan)
    raw = mz * 0.8 + ts * 5 + (rel_vol - 1) * 1.2 + adx / 25
    ai = (100 / (1 + np.exp(-raw))) * (1 + (vr - 1) * 0.5)
    ai = ai.clip(5, 95)
    # ABC grade
    ema10 = c.ewm(span=10, adjust=False).mean()
    ema20 = c.ewm(span=20, adjust=False).mean()
    sma50 = c.rolling(50).mean()
    return {
        "score": score, "ai": ai, "rsi": rsi, "adx": adx,
        "ext": ext, "rel_vol": rel_vol, "ema50": ema50, "ema200": ema200,
        "ema10": ema10, "ema20": ema20, "sma50": sma50, "atr": atr,
    }

def abc_grade(ema10, ema20, sma50):
    if pd.isna(ema10) or pd.isna(ema20) or pd.isna(sma50): return None
    if ema10 > ema20 > sma50: return "A"
    if ema10 < ema20 < sma50: return "C"
    return "B"

# ═══ HESSIAN MATRIX COMPUTATION ══════════════════════════════════
# Applies Hessian Matrix (second-order partial derivatives) to detect
# curvature of price-volume surface → local minima (buy), maxima (sell), saddle (wait)
def compute_hessian(hist, window=20):
    """
    Compute 2D Hessian Matrix H = [[fxx, fxy], [fxy, fyy]] where:
    - f_xx = d²Price/dt² (price acceleration)
    - f_yy = d²Volume/dt² (volume acceleration)  
    - f_xy = cross-derivative (price-volume coupling)
    
    Returns DataFrame with Hessian metrics per bar.
    """
    c = hist["Close"].copy()
    v = hist["Volume"].copy()
    
    # Normalize: percentage changes for scale-invariance
    price_ret = c.pct_change().fillna(0) * 100  # Daily returns %
    vol_ret = v.pct_change().fillna(0) * 100     # Volume change %
    
    # First derivatives (velocity): rolling mean of changes
    dp = price_ret.rolling(window).mean()   # Price velocity
    dv = vol_ret.rolling(window).mean()     # Volume velocity
    
    # Second derivatives (acceleration): change of velocity
    fxx = dp.diff().rolling(window).mean()  # Price acceleration
    fyy = dv.diff().rolling(window).mean()  # Volume acceleration
    
    # Cross derivative: rolling covariance of price_ret and vol_ret changes
    fxy = price_ret.diff().rolling(window).apply(
        lambda x: np.corrcoef(x, vol_ret.diff().iloc[x.index[0]-c.index[0]:x.index[-1]-c.index[0]+1].values[:len(x)])[0,1] 
        if len(x) > 2 else 0, raw=False
    ) if len(c) > window*3 else pd.Series(0, index=c.index)
    
    # Simpler cross-derivative: rolling correlation of first derivative changes
    dp_diff = price_ret.diff().fillna(0)
    dv_diff = vol_ret.diff().fillna(0)
    fxy = dp_diff.rolling(window).corr(dv_diff).fillna(0) * (fxx.abs() * fyy.abs()).apply(np.sqrt)
    
    # Determinant: D = fxx*fyy - fxy²
    det = fxx * fyy - fxy * fxy
    
    # Trace: tr(H) = fxx + fyy
    trace = fxx + fyy
    
    # Eigenvalues: λ = (tr ± √(tr²-4D)) / 2
    disc = trace * trace - 4 * det
    disc_safe = disc.clip(lower=0)
    lam1 = (trace + np.sqrt(disc_safe)) / 2
    lam2 = (trace - np.sqrt(disc_safe)) / 2
    
    # Curvature magnitude
    curvature = (fxx**2 + 2*fxy**2 + fyy**2).apply(np.sqrt)
    
    return {
        "fxx": fxx, "fyy": fyy, "fxy": fxy,
        "det": det, "trace": trace,
        "lam1": lam1, "lam2": lam2,
        "curvature": curvature,
    }

def classify_hessian(fxx, det):
    """Classify point using Second Derivative Test."""
    if pd.isna(fxx) or pd.isna(det):
        return "UNDEFINED", "⚪"
    if det > 0.001 and fxx > 0.001:
        return "LOCAL_MIN", "🟢"    # Convex → price at bottom → BUY
    elif det > 0.001 and fxx < -0.001:
        return "LOCAL_MAX", "🔴"    # Concave → price at top → AVOID
    elif det < -0.001:
        return "SADDLE", "🟡"       # Saddle point → unstable → WAIT
    else:
        return "FLAT", "⚪"         # Near zero → no curvature → NEUTRAL

def compute_state(score, ai, ext, fund_score=None):
    if score >= 75 and ai > 70 and ext < 12:
        if fund_score and fund_score >= 60: return "ENTRY+"
        return "ENTRY"
    if score >= 60 and ai > 60: return "ACCUM"
    return "WAIT"

# ── FUNDAMENTAL GRADES ───────────────────────────────────────────
def grade_pe(v):
    if v is None or np.isnan(v): return "N/A", None
    if v < 0: return "Loss", 0
    if v < 15: return "Cheap", 3
    if v < 25: return "Fair", 2
    if v < 40: return "Pricey", 1
    return "Overval", 0

def grade_roe(v):
    if v is None or np.isnan(v): return "N/A", None
    if v > 20: return "Excel", 3
    if v > 15: return "Good", 2
    if v > 10: return "Med", 1
    return "Weak", 0

def grade_roa(v):
    if v is None or np.isnan(v): return "N/A", None
    if v > 10: return "Excel", 3
    if v > 5: return "Good", 2
    if v > 3: return "Med", 1
    return "Weak", 0

def grade_eps(v):
    if v is None or np.isnan(v): return "N/A", None
    if v > 25: return "Strong", 3
    if v > 10: return "Solid", 2
    if v > 0: return "Mod", 1
    return "Decl", 0

def safe_float(info, key):
    try:
        v = info.get(key)
        if v is None or v == "N/A": return None
        f = float(v)
        return f if np.isfinite(f) else None
    except: return None

def safe_pct(info, key):
    v = safe_float(info, key)
    if v is not None and abs(v) < 10: return round(v * 100, 2)
    return v

# ── PRICE PROJECTION ─────────────────────────────────────────────
def compute_projection(close, ema50, ema200, atr, rsi, score, ai, pe, sector_pe=20):
    """Quantitative price projection for LONG bias."""
    if close is None or np.isnan(close) or atr is None or np.isnan(atr):
        return None, None, None
    # Technical target: based on ATR extension and trend
    tech_upside = atr * 3  # 3 ATR upside target
    tech_target = close + tech_upside
    # Momentum adjustment
    if score >= 75 and ai > 70:
        tech_target *= 1.05  # Strong momentum bonus
    elif score < 40:
        tech_target *= 0.95  # Weak momentum penalty
    # Fundamental adjustment via P/E
    if pe and pe > 0 and sector_pe and sector_pe > 0:
        pe_ratio = sector_pe / pe
        if pe_ratio > 1.3:  # Undervalued
            tech_target *= 1.03
        elif pe_ratio < 0.6:  # Very overvalued
            tech_target *= 0.97
    # Confidence based on RSI + Score alignment
    if score >= 75 and 45 < rsi < 65:
        confidence = "High"
    elif score >= 60:
        confidence = "Med"
    else:
        confidence = "Low"
    pct_upside = ((tech_target / close) - 1) * 100
    return round(tech_target, 2), round(pct_upside, 1), confidence

# ═══ REAL BACKTESTING ENGINE ══════════════════════════════════════
# Uses historical prices + our SAME indicators to test signals in the past.
# No simulation — only real price movements.

HOLD_PERIODS = [
    {"label": "1 Semana", "days": 5,   "key": "1w"},
    {"label": "1 Mes",    "days": 21,  "key": "1m"},
    {"label": "3 Meses",  "days": 63,  "key": "3m"},
    {"label": "6 Meses",  "days": 126, "key": "6m"},
    {"label": "1 Año",    "days": 252, "key": "1y"},
]

def run_backtest_for_ticker(ticker, hist, ind, fund_data, is_etf=False):
    """
    Walk through historical data applying our 4-layer signal criteria.
    When signal triggers, measure REAL forward price change.
    
    Returns dict with results per holding period.
    """
    closes = hist["Close"]
    n = len(closes)
    
    # We need at least 252 bars of warmup + 252 bars of forward data
    # So we check signals from bar 200 onward, with step of 5 (weekly checks)
    start_bar = min(200, n - 60)  # Need at least some warmup
    if start_bar < 50:
        return None
    
    # Extract current fundamentals (proxy — yfinance doesn't provide historical fundamentals)
    pe = fund_data.get('pe')
    roe = fund_data.get('roe', 0) or 0
    roa = fund_data.get('roa', 0) or 0
    eps_g = fund_data.get('eps_g', 0) or 0
    fund_score = fund_data.get('fund')
    
    # Pre-compute grade scores for fundamentals (constant for the year)
    pe_gr_s = grade_pe(pe)[1] or 0
    roe_gr_s = grade_roe(roe)[1] or 0
    roa_gr_s = grade_roa(roa)[1] or 0
    eps_gr_s = grade_eps(eps_g)[1] or 0
    pts = [p for p in [pe_gr_s, roe_gr_s, roa_gr_s, eps_gr_s] if p is not None]
    composite = round(sum(pts) / (len(pts) * 3) * 100, 0) if pts else 0
    
    # Earnings quality check
    earnings_suspicious = (eps_gr_s >= 2 and roa_gr_s <= 0)
    # Debt risk check
    debt_high = (roe > 0 and roa > 0 and roe / max(roa, 0.01) > 3)
    
    # Results structure
    entry_trades = {p["key"]: [] for p in HOLD_PERIODS}  # Entry Zone trades (strict 4/4)
    tech_trades = {p["key"]: [] for p in HOLD_PERIODS}   # Technical signals (L1+L3 only)
    gt_trades = {p["key"]: {"nash": [], "bayesian": [], "sequential": []} for p in HOLD_PERIODS}
    hessian_trades = {p["key"]: [] for p in HOLD_PERIODS}  # Hessian local minimum signals
    
    # Pre-compute Hessian for entire history
    try:
        hess = compute_hessian(hist, window=20)
    except:
        hess = None
    
    # Walk through history (check every 5 bars = weekly)
    for i in range(start_bar, n, 5):
        sc = float(ind["score"].iloc[i]) if not pd.isna(ind["score"].iloc[i]) else 0
        ai_v = float(ind["ai"].iloc[i]) if not pd.isna(ind["ai"].iloc[i]) else 50
        rsi_v = float(ind["rsi"].iloc[i]) if not pd.isna(ind["rsi"].iloc[i]) else 50
        adx_v = float(ind["adx"].iloc[i]) if not pd.isna(ind["adx"].iloc[i]) else 15
        ext_v = float(ind["ext"].iloc[i]) if not pd.isna(ind["ext"].iloc[i]) else 0
        rv = float(ind["rel_vol"].iloc[i]) if not pd.isna(ind["rel_vol"].iloc[i]) else 1
        
        e10 = float(ind["ema10"].iloc[i]) if not pd.isna(ind["ema10"].iloc[i]) else None
        e20 = float(ind["ema20"].iloc[i]) if not pd.isna(ind["ema20"].iloc[i]) else None
        s50 = float(ind["sma50"].iloc[i]) if not pd.isna(ind["sma50"].iloc[i]) else None
        abc = abc_grade(e10, e20, s50)
        state = compute_state(sc, ai_v, ext_v, fund_score)
        
        close_price = float(closes.iloc[i])
        date_str = str(hist.index[i].date()) if hasattr(hist.index[i], 'date') else str(hist.index[i])[:10]
        
        # Momentum at this point
        d5 = ((closes.iloc[i] / closes.iloc[i-5]) - 1) * 100 if i >= 5 else 0
        d20 = ((closes.iloc[i] / closes.iloc[i-20]) - 1) * 100 if i >= 20 else 0
        
        # ═══ 4-LAYER VALIDATION (same criteria as check_alerts.py) ═══
        
        # Layer 1: Radar (slightly relaxed for historical — signals were valid at their time)
        if is_etf:
            l1 = sc >= 25 and d20 > -8
        else:
            l1 = (state in ('ENTRY+', 'ENTRY', 'ACCUM') and sc >= 50 and ai_v >= 55 
                  and abc in ('A', 'B') and rsi_v < 78)
        
        # Layer 2: Analysis (fundamentals — constant proxy, relaxed for history)
        if is_etf:
            l2 = sc >= 25 and d20 > -8
        else:
            l2 = (composite >= 45 and roe >= 5 and roa >= 2 
                  and not earnings_suspicious and not debt_high)
        
        # Layer 3: Entry Zones (momentum check, relaxed for history)
        if is_etf:
            l3 = d20 > -5 and d5 > -8
        else:
            l3 = d20 > -3 and d5 > -8
        
        # Layer 4: Game Theory (Bayesian probability)
        prior = 0.5
        lk_ai = ai_v / 100
        lk_vol = 1.3 if rv > 1.1 else 0.9
        lk_rsi = 1.2 if (40 < rsi_v < 70) else 0.7
        lk_fund = composite / 85 if composite > 0 else 0.5
        lk_mom = 1.2 if d20 > 3 else (1.0 if d20 > 0 else 0.7)
        lk_adx = 1.15 if adx_v > 20 else 0.85
        bayesian_prob = min(0.95, max(0.15, prior * lk_ai * lk_vol * lk_rsi * lk_fund * lk_mom * lk_adx * 3.5))
        
        if is_etf:
            l4 = bayesian_prob >= 0.45
        else:
            l4 = bayesian_prob >= 0.55
        
        all_pass = l1 and l2 and l3 and l4
        # Technical-only signal (L1 + L3 — these actually change historically)
        tech_pass = l1 and l3
        
        # ═══ MEASURE REAL FORWARD RETURNS ═══
        for period in HOLD_PERIODS:
            exit_bar = i + period["days"]
            if exit_bar >= n:
                continue  # Not enough future data
            
            exit_price = float(closes.iloc[exit_bar])
            real_pnl = ((exit_price / close_price) - 1) * 100
            real_pnl = round(real_pnl, 2)
            
            trade = {
                "date": date_str,
                "entry": round(close_price, 2),
                "exit": round(exit_price, 2),
                "pnl": real_pnl,
                "win": real_pnl > 0,
                "score": int(sc),
                "ai": round(ai_v, 1),
                "rsi": round(rsi_v, 1),
                "state": state,
                "prob": round(bayesian_prob * 100),
            }
            
            # Entry Zone backtest: only when ALL 4 layers pass
            if all_pass:
                entry_trades[period["key"]].append(trade)
            
            # Technical signal backtest: when L1 (Radar) + L3 (Momentum) pass
            if tech_pass:
                tech_trades[period["key"]].append(trade)
            
            # Hessian signal: D > 0 and fxx > 0 → local minimum → potential reversal up
            if hess is not None and i < len(hess["det"]):
                h_fxx_i = hess["fxx"].iloc[i] if not pd.isna(hess["fxx"].iloc[i]) else 0
                h_det_i = hess["det"].iloc[i] if not pd.isna(hess["det"].iloc[i]) else 0
                h_class_i, _ = classify_hessian(h_fxx_i, h_det_i)
                if h_class_i == "LOCAL_MIN" and d20 > -10:  # Local minimum + not in freefall
                    hessian_trades[period["key"]].append(trade)
            
            # Game Theory backtest: different per model
            # Nash: balanced (l1 or l2 combined with l3 and moderate l4)
            nash_pass = (l1 or l2) and l3 and bayesian_prob >= 0.45
            if nash_pass:
                gt_trades[period["key"]]["nash"].append(trade)
            
            # Bayesian: heavy AI weight (l2 + decent probability + ai >= 55)
            bay_pass = l2 and bayesian_prob >= 0.50 and ai_v >= 55 and d20 > -5
            if bay_pass:
                gt_trades[period["key"]]["bayesian"].append(trade)
            
            # Sequential: signal-based (state active + momentum)
            seq_pass = state in ('ENTRY+', 'ENTRY', 'ACCUM') and l3 and sc >= 45
            if seq_pass:
                gt_trades[period["key"]]["sequential"].append(trade)
    
    # ═══ COMPILE STATISTICS ═══
    def calc_stats(trades_list):
        if not trades_list:
            return {"n": 0, "wins": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0,
                    "max_win": 0, "max_loss": 0, "profit_factor": 0, "trades": []}
        n = len(trades_list)
        wins = sum(1 for t in trades_list if t["win"])
        pnls = [t["pnl"] for t in trades_list]
        gross_win = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        return {
            "n": n,
            "wins": wins,
            "win_rate": round(wins / n * 100, 1) if n else 0,
            "avg_pnl": round(sum(pnls) / n, 2) if n else 0,
            "total_pnl": round(sum(pnls), 2),
            "max_win": round(max(pnls), 2) if pnls else 0,
            "max_loss": round(min(pnls), 2) if pnls else 0,
            "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (99 if gross_win > 0 else 0),
            "trades": trades_list[-20:]  # Last 20 trades for display
        }
    
    result = {
        "ticker": ticker,
        "name": fund_data.get('name', ticker),
        "sector": fund_data.get('sector', 'N/A'),
        "is_etf": is_etf,
        "composite": composite,
        "data_bars": n,
        "entry_zones": {},
        "tech_signals": {},
        "hessian_signals": {},
        "game_theory": {},
    }
    
    for p in HOLD_PERIODS:
        result["entry_zones"][p["key"]] = calc_stats(entry_trades[p["key"]])
        result["tech_signals"][p["key"]] = calc_stats(tech_trades[p["key"]])
        result["hessian_signals"][p["key"]] = calc_stats(hessian_trades[p["key"]])
        result["game_theory"][p["key"]] = {
            "nash": calc_stats(gt_trades[p["key"]]["nash"]),
            "bayesian": calc_stats(gt_trades[p["key"]]["bayesian"]),
            "sequential": calc_stats(gt_trades[p["key"]]["sequential"]),
        }
    
    return result


def run_full_backtest(groups_data, out_dir):
    """Run backtest for all tickers and save results."""
    print(f"\n{'='*55}")
    print(f"BACKTESTING — Using real historical prices")
    print(f"{'='*55}")
    
    ETF_SECTORS = {'Index', 'ETF', 'Commodity', 'Fixed Income', ''}
    all_results = []
    
    all_tickers = set()
    for gn, rows in groups_data.items():
        for r in rows:
            all_tickers.add((r['ticker'], r.get('sector', 'N/A'), gn))
    
    for i, (ticker, sector, group) in enumerate(sorted(all_tickers)):
        print(f"  BT [{i+1}/{len(all_tickers)}] {ticker}...", end=" ")
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2y", auto_adjust=True)
            if hist is None or len(hist) < 120:
                print("skip (not enough data)")
                continue
            
            ind = compute_score(hist)
            
            # Get fund data from snapshot
            fund_data = {}
            for gn, rows in groups_data.items():
                for r in rows:
                    if r['ticker'] == ticker:
                        fund_data = r
                        break
            
            is_etf = sector in ETF_SECTORS
            result = run_backtest_for_ticker(ticker, hist, ind, fund_data, is_etf)
            
            if result:
                result['group'] = group
                all_results.append(result)
                # Quick summary
                ez_1m = result['entry_zones'].get('1m', {})
                if ez_1m.get('n', 0) > 0:
                    print(f"EZ: {ez_1m['n']} trades, {ez_1m['win_rate']}% WR, avg {ez_1m['avg_pnl']}%")
                else:
                    print(f"no EZ signals (criteria too strict for history)")
            else:
                print("skip")
        except Exception as e:
            print(f"error: {e}")
        time.sleep(0.15)
    
    # Save
    bt_path = os.path.join(out_dir, "backtest.json")
    bt_data = {
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "Real historical prices — Yahoo Finance 2-year data",
        "layers": "4-layer validation: Radar + Analysis + Entry Zones + Game Theory",
        "note": "Fundamentals (P/E, ROE, ROA) use current values as proxy — historical fundamentals not available via free API",
        "total_tickers": len(all_results),
        "results": all_results,
    }
    with open(bt_path, "w", encoding="utf-8") as f:
        json.dump(bt_data, f, ensure_ascii=False, indent=2)
    print(f"\nBacktest saved: {bt_path} — {len(all_results)} tickers tested")
    return bt_data


# ── MAIN BUILD ───────────────────────────────────────────────────
def get_stock_data(ticker, spy_close=None):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y", auto_adjust=True)
        if hist is None or len(hist) < 60:
            return None
        # Anti-repaint: drop today's potentially incomplete candle
        now = datetime.now()
        if hasattr(hist.index[-1], 'date') and hist.index[-1].date() == now.date():
            hist = hist.iloc[:-1]
        if len(hist) < 60:
            return None
        ind = compute_score(hist)
        last = -1  # last closed candle
        close = float(hist["Close"].iloc[last])
        sc = float(ind["score"].iloc[last])
        ai_p = float(ind["ai"].iloc[last])
        rsi_v = float(ind["rsi"].iloc[last]) if not pd.isna(ind["rsi"].iloc[last]) else None
        adx_v = float(ind["adx"].iloc[last]) if not pd.isna(ind["adx"].iloc[last]) else None
        ext_v = float(ind["ext"].iloc[last]) if not pd.isna(ind["ext"].iloc[last]) else None
        rv = float(ind["rel_vol"].iloc[last]) if not pd.isna(ind["rel_vol"].iloc[last]) else None
        abc = abc_grade(
            float(ind["ema10"].iloc[last]) if not pd.isna(ind["ema10"].iloc[last]) else None,
            float(ind["ema20"].iloc[last]) if not pd.isna(ind["ema20"].iloc[last]) else None,
            float(ind["sma50"].iloc[last]) if not pd.isna(ind["sma50"].iloc[last]) else None,
        )
        atr_v = float(ind["atr"].iloc[last]) if not pd.isna(ind["atr"].iloc[last]) else None
        # Performance
        daily = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100 if len(hist) >= 2 else None
        five_d = (hist["Close"].iloc[-1] / hist["Close"].iloc[-6] - 1) * 100 if len(hist) >= 6 else None
        twenty_d = (hist["Close"].iloc[-1] / hist["Close"].iloc[-21] - 1) * 100 if len(hist) >= 21 else None
        # Fundamentals
        pe, roe, roa, eps_g = None, None, None, None
        name, sector, mktcap = ticker, "N/A", None
        try:
            info = stock.info
            pe = safe_float(info, "trailingPE")
            roe = safe_pct(info, "returnOnEquity")
            roa = safe_pct(info, "returnOnAssets")
            eps_g = safe_pct(info, "earningsQuarterlyGrowth")
            name = info.get("shortName", ticker)
            sector = info.get("sector", "N/A")
            mktcap = safe_float(info, "marketCap")
        except: pass
        pe_gr, pe_pts = grade_pe(pe)
        roe_gr, roe_pts = grade_roe(roe)
        roa_gr, roa_pts = grade_roa(roa)
        eps_gr, eps_pts = grade_eps(eps_g)
        pts = [p for p in [pe_pts, roe_pts, roa_pts, eps_pts] if p is not None]
        fund_score = round(sum(pts) / (len(pts) * 3) * 100, 0) if pts else None
        state = compute_state(sc, ai_p, ext_v or 0, fund_score)
        # Projection
        tgt, upside, conf = compute_projection(close, 
            float(ind["ema50"].iloc[last]) if not pd.isna(ind["ema50"].iloc[last]) else close,
            float(ind["ema200"].iloc[last]) if not pd.isna(ind["ema200"].iloc[last]) else close,
            atr_v, rsi_v or 50, sc, ai_p, pe)
        # Market cap format
        mc_str = "N/A"
        if mktcap:
            if mktcap >= 1e12: mc_str = f"${mktcap/1e12:.1f}T"
            elif mktcap >= 1e9: mc_str = f"${mktcap/1e9:.0f}B"
            elif mktcap >= 1e6: mc_str = f"${mktcap/1e6:.0f}M"
        # Hessian Matrix computation
        hess_data = {}
        try:
            hess = compute_hessian(hist, window=20)
            h_fxx = float(hess["fxx"].iloc[-1]) if not pd.isna(hess["fxx"].iloc[-1]) else 0
            h_fyy = float(hess["fyy"].iloc[-1]) if not pd.isna(hess["fyy"].iloc[-1]) else 0
            h_fxy = float(hess["fxy"].iloc[-1]) if not pd.isna(hess["fxy"].iloc[-1]) else 0
            h_det = float(hess["det"].iloc[-1]) if not pd.isna(hess["det"].iloc[-1]) else 0
            h_trace = float(hess["trace"].iloc[-1]) if not pd.isna(hess["trace"].iloc[-1]) else 0
            h_lam1 = float(hess["lam1"].iloc[-1]) if not pd.isna(hess["lam1"].iloc[-1]) else 0
            h_lam2 = float(hess["lam2"].iloc[-1]) if not pd.isna(hess["lam2"].iloc[-1]) else 0
            h_curv = float(hess["curvature"].iloc[-1]) if not pd.isna(hess["curvature"].iloc[-1]) else 0
            h_class, h_icon = classify_hessian(h_fxx, h_det)
            hess_data = {
                "fxx": round(h_fxx, 4), "fyy": round(h_fyy, 4), "fxy": round(h_fxy, 4),
                "det": round(h_det, 4), "trace": round(h_trace, 4),
                "lam1": round(h_lam1, 4), "lam2": round(h_lam2, 4),
                "curvature": round(h_curv, 4),
                "class": h_class, "icon": h_icon,
            }
        except: pass
        return {
            "ticker": ticker, "name": name[:22], "close": round(close, 2),
            "score": int(sc), "ai": round(ai_p, 1),
            "state": state, "abc": abc,
            "rsi": round(rsi_v, 1) if rsi_v else None,
            "adx": round(adx_v, 1) if adx_v else None,
            "ext": round(ext_v, 1) if ext_v else None,
            "rel_vol": round(rv, 2) if rv else None,
            "daily": round(daily, 2) if daily else None,
            "5d": round(five_d, 2) if five_d else None,
            "20d": round(twenty_d, 2) if twenty_d else None,
            "pe": round(pe, 1) if pe else None, "pe_gr": pe_gr,
            "roe": round(roe, 1) if roe else None, "roe_gr": roe_gr,
            "roa": round(roa, 1) if roa else None, "roa_gr": roa_gr,
            "eps_g": round(eps_g, 1) if eps_g else None, "eps_gr": eps_gr,
            "fund": fund_score, "sector": sector, "mktcap": mc_str,
            "target": tgt, "upside": upside, "proj_conf": conf,
            "hessian": hess_data,
        }
    except Exception as e:
        print(f"  ERROR {ticker}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--skip-backtest", action="store_true", help="Skip heavy backtest (for quick 5-min updates)")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    print(f"ZENITH SCANNER PRO — Building data at {datetime.now()}")
    groups_data = {}
    for group_name, tickers in GROUPS.items():
        rows = []
        seen = set()
        for i, t in enumerate(tickers):
            if t in seen: continue
            seen.add(t)
            print(f"  [{group_name}] {i+1}/{len(tickers)} {t}")
            row = get_stock_data(t)
            if row: rows.append(row)
            time.sleep(0.2)
        groups_data[group_name] = rows
    # Column ranges for visual bars
    col_ranges = {}
    for gn, rows in groups_data.items():
        vals = lambda k: [r[k] for r in rows if r.get(k) is not None]
        for k in ["daily", "5d", "20d"]:
            v = vals(k)
            col_ranges.setdefault(gn, {})[k] = [min(v) if v else -5, max(v) if v else 5]
    snapshot = {
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "groups": groups_data,
        "column_ranges": col_ranges,
    }
    path = os.path.join(args.out_dir, "snapshot.json")
    total_tickers = sum(len(r) for r in groups_data.values())
    
    # Safety: don't overwrite a working file with empty/broken data
    if total_tickers < 10 and os.path.exists(path):
        print(f"\n⚠️ Only {total_tickers} tickers loaded (expected 200+). Keeping existing snapshot.json.")
        print(f"  This usually means Yahoo Finance is rate-limiting or unavailable.")
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {path} — {total_tickers} tickers processed")
    
    # Run real backtest with historical data (skip on quick 5-min updates)
    if not args.skip_backtest:
        run_full_backtest(groups_data, args.out_dir)
    else:
        print("  ⏭ Backtest skipped (--skip-backtest flag)")

if __name__ == "__main__":
    main()
