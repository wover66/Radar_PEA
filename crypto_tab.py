"""Onglet Crypto — Scanner de gems via DexScreener (interface Streamlit)."""

import html
import time
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

import sys, os
sys.path.insert(0, os.path.expanduser("~"))

from gem_evaluator import (
    fetch_latest_profiles, fetch_boosted_tokens, fetch_pairs_for_token,
    evaluate_pair, score_pair, volume_momentum,
    CHAINS, BLACKLIST,
)

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_MIN_LIQ    = 250_000
DEFAULT_MIN_MCAP   = 2_000_000
DEFAULT_MAX_MCAP   = 10_000_000
DEFAULT_MIN_MOM    = 1.5
DEFAULT_MIN_VOL24  = 50_000
DEFAULT_MAX_CHANGE = 500
MAX_TOKENS         = 60
BATCH_PAUSE        = 1.0

CHAIN_COLORS = {
    "Solana":    "#9945ff",
    "Base":      "#4a7bff",
    "BNB Chain": "#f0b90b",
    "Arbitrum":  "#28a0f0",
    "Polygon":   "#a78bfa",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val: float) -> str:
    if val >= 1_000_000: return f"${val/1_000_000:.2f}M"
    if val >= 1_000:     return f"${val/1_000:.1f}K"
    return f"${val:.0f}"

def _cls(val: float) -> str:
    return "green" if val > 0.5 else ("red" if val < -0.5 else "")

def _var_html(val: float) -> str:
    cls = _cls(val)
    arr = "▲" if val > 0 else "▼" if val < 0 else "→"
    return f'<span class="{cls}" style="font-weight:600">{arr} {val:+.1f}%</span>'


# ── Scan paramétrable ─────────────────────────────────────────────────────────

def collect_pairs_st(tokens, chains, max_tokens, batch_pause, progress_bar, status):
    """Version Streamlit-aware de collect_pairs (barre de progression live)."""
    import requests
    pairs = {}
    filtered = [t for t in tokens if t.get("chainId") in chains][:max_tokens]
    total = len(filtered)
    for i, token in enumerate(filtered):
        addr = token.get("tokenAddress") or token.get("address")
        if not addr:
            continue
        try:
            for p in fetch_pairs_for_token(addr):
                pa = p.get("pairAddress")
                if pa:
                    pairs[pa] = p
        except Exception:
            pass
        progress_bar.progress(min((i + 1) / max(total, 1), 1.0),
                              text=f"Analyse {i+1}/{total}…")
        if (i + 1) % 10 == 0:
            time.sleep(batch_pause)
    return pairs


def run_scan(cfg: dict) -> dict:
    """Lance le scan complet et retourne les résultats."""
    import requests

    def evaluate_with_cfg(pair):
        if pair.get("chainId") not in cfg["chains"]:
            return None
        base     = pair.get("baseToken") or {}
        name_sym = (base.get("name","") + " " + base.get("symbol","")).lower()
        if any(kw in name_sym for kw in BLACKLIST):
            return None
        info     = pair.get("info") or {}
        if not (info.get("websites") or []):
            return None
        socials  = info.get("socials") or []
        has_twitter = any(
            s.get("type","").lower() == "twitter" or
            "twitter" in (s.get("url") or "").lower() or
            "x.com"   in (s.get("url") or "").lower()
            for s in socials
        )
        if not has_twitter:
            return None
        liq   = (pair.get("liquidity") or {}).get("usd") or 0
        mcap  = pair.get("marketCap") or pair.get("fdv") or 0
        vol24 = (pair.get("volume") or {}).get("h24") or 0
        mom   = volume_momentum(pair)
        if liq  < cfg["min_liq"]:   return None
        if not (cfg["min_mcap"] <= mcap <= cfg["max_mcap"]): return None
        if vol24 < cfg["min_vol24"]: return None
        if mom   < cfg["min_mom"]:  return None
        chg = pair.get("priceChange") or {}
        if (abs(chg.get("h1") or 0) > cfg["max_change"] or
                abs(chg.get("h6") or 0) > cfg["max_change"]):
            return None
        vol = pair.get("volume") or {}
        return {
            "chain": CHAINS[pair["chainId"]], "name": base.get("name","?"),
            "symbol": base.get("symbol","?"), "address": base.get("address",""),
            "price_usd": pair.get("priceUsd","?"), "market_cap": mcap,
            "liquidity": liq, "vol_h1": vol.get("h1") or 0,
            "vol_h6": vol.get("h6") or 0, "vol_h24": vol24, "momentum": round(mom,2),
            "chg_h1":  chg.get("h1") or 0, "chg_h6":  chg.get("h6") or 0,
            "chg_h24": chg.get("h24") or 0,
            "url": pair.get("url",""), "score": score_pair(pair),
        }

    t0 = time.time()
    all_pairs = {}

    pbar   = st.progress(0, text="Récupération des tokens récents…")
    status = st.empty()

    try:
        profiles = fetch_latest_profiles()
        status.caption(f"[1/2] Profils récents — {len(profiles)} tokens")
        all_pairs |= collect_pairs_st(profiles, cfg["chains"], MAX_TOKENS,
                                      BATCH_PAUSE, pbar, status)
    except Exception as e:
        status.caption(f"⚠️ Profils : {e}")

    try:
        pbar.progress(0, text="Récupération des tokens boostés…")
        boosted = fetch_boosted_tokens()
        status.caption(f"[2/2] Tokens boostés — {len(boosted)} tokens")
        all_pairs |= collect_pairs_st(boosted, cfg["chains"], MAX_TOKENS,
                                      BATCH_PAUSE, pbar, status)
    except Exception as e:
        status.caption(f"⚠️ Boostés : {e}")

    pbar.progress(1.0, text="Évaluation des paires…")
    gems = [r for p in all_pairs.values() if (r := evaluate_with_cfg(p))]
    gems.sort(key=lambda x: x["score"], reverse=True)

    seen, unique = set(), []
    for g in gems:
        key = g["address"] or g["name"]
        if key not in seen:
            seen.add(key); unique.append(g)

    pbar.empty(); status.empty()
    return {"gems": unique, "scanned": len(all_pairs), "duration": time.time() - t0,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}


# ── Tableau HTML gems ─────────────────────────────────────────────────────────

def render_gem_table(gems: list) -> str:
    if not gems:
        return '<div style="text-align:center;padding:40px;color:#8b949e">Aucun gem détecté.</div>'
    rows = []
    for i, g in enumerate(gems[:20], 1):
        color = CHAIN_COLORS.get(g["chain"], "#a78bfa")
        mom_pct = min(g["momentum"] / 6.0, 1.0) * 100
        rows.append(f"""<tr>
          <td class="rank">{i}</td>
          <td><div class="nom-main">{html.escape(g['name'])}</div>
              <div class="nom-sub">{g['symbol']}</div></td>
          <td><span class="badge" style="background:{color}1a;color:{color};
              border:1px solid {color}40">{g['chain']}</span></td>
          <td style="color:#e6edf3;font-weight:700;font-family:'JetBrains Mono',monospace;font-size:12px">${g['price_usd']}</td>
          <td style="color:rgba(201,209,217,0.8);font-family:'JetBrains Mono',monospace;font-size:12px">{_fmt(g['market_cap'])}</td>
          <td style="color:rgba(201,209,217,0.8);font-family:'JetBrains Mono',monospace;font-size:12px">{_fmt(g['liquidity'])}</td>
          <td>
            <div style="background:rgba(30,42,58,0.8);border-radius:4px;height:4px;width:68px;
                display:inline-block;vertical-align:middle;border:1px solid rgba(255,255,255,0.04)">
              <div style="height:100%;width:{mom_pct:.0f}%;
                  background:linear-gradient(90deg,#00d4aa,#a78bfa);border-radius:4px;
                  box-shadow:0 0 6px rgba(0,212,170,0.4)"></div>
            </div>
            <span style="color:#a78bfa;font-weight:800;margin-left:8px;font-size:12px">{g['momentum']}x</span>
          </td>
          <td>{_var_html(g['chg_h1'])}</td>
          <td>{_var_html(g['chg_h6'])}</td>
          <td>{_var_html(g['chg_h24'])}</td>
          <td style="color:#e3b341;font-weight:900;font-size:15px;font-family:'JetBrains Mono',monospace">{g['score']}</td>
          <td><a href="{g['url']}" target="_blank"
              style="color:#a78bfa;text-decoration:none;border:1px solid rgba(124,58,237,0.3);
              padding:5px 12px;border-radius:8px;font-size:11px;font-weight:600;
              background:rgba(124,58,237,0.06);transition:all 0.2s;white-space:nowrap">→ DEX</a></td>
        </tr>""")
    return f"""<div class="cg-wrap"><table class="cg-table">
  <thead><tr><th>#</th><th>Token</th><th>Chain</th><th>Prix</th>
  <th>MCap</th><th>Liquidité</th><th>Momentum</th>
  <th>Var 1h</th><th>Var 6h</th><th>Var 24h</th><th>Score</th><th>Lien</th>
  </tr></thead><tbody>{"".join(rows)}</tbody></table></div>"""


# ── Render principal ──────────────────────────────────────────────────────────

def render():
    # ── Sidebar Crypto ────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Filtres Crypto")

        with st.expander("🔗 Blockchains", expanded=True):
            all_chains = list(CHAINS.keys())
            sel_chains = st.multiselect(
                "Chains", all_chains, default=all_chains,
                format_func=lambda x: CHAINS[x],
            )

        with st.expander("📊 Critères financiers", expanded=True):
            min_liq  = st.number_input("Liquidité min ($)", value=DEFAULT_MIN_LIQ,
                                        step=50_000, format="%d")
            min_mcap = st.number_input("MCap min ($)", value=DEFAULT_MIN_MCAP,
                                        step=500_000, format="%d")
            max_mcap = st.number_input("MCap max ($)", value=DEFAULT_MAX_MCAP,
                                        step=1_000_000, format="%d")
            min_mom  = st.slider("Momentum min (6h/24h)", 1.0, 5.0,
                                  DEFAULT_MIN_MOM, 0.1)
            max_chg  = st.slider("Variation max anti-pump (%)", 50, 1000,
                                  DEFAULT_MAX_CHANGE, 50)

        if st.button("🗑️ Effacer résultats", use_container_width=True):
            for k in ["crypto_result"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # ── Bannière ──────────────────────────────────────────────────────────────
    st.markdown("""<div class="radar-banner">
      <h1 style="background:linear-gradient(90deg,#a78bfa 0%,#42a5f5 40%,#00d4aa 100%);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
         ⚡ ÉVALUATEUR CRYPTO — GEMS</h1>
      <p>Scanner DexScreener &nbsp;·&nbsp; Solana · Base · BNB · Arbitrum · Polygon &nbsp;·&nbsp; Détection d'accumulation</p>
    </div>""", unsafe_allow_html=True)

    # ── Avertissement ─────────────────────────────────────────────────────────
    st.markdown("""<div class="crypto-warn">
      ⚠️ <strong>Avertissement</strong> — Ces données sont fournies à titre informatif uniquement.
      Les tokens de faible capitalisation comportent des risques extrêmes : rug pull, manipulation
      de prix, volatilité extrême. Ne prenez aucune décision d'investissement sur la base de cet
      outil seul.
    </div>""", unsafe_allow_html=True)

    # ── Bouton de scan ────────────────────────────────────────────────────────
    col_btn, col_ts = st.columns([1, 3])
    with col_btn:
        launch = st.button("🔍 Lancer le scan", type="primary", use_container_width=True)
    with col_ts:
        if "crypto_result" in st.session_state:
            res = st.session_state["crypto_result"]
            st.caption(f"Dernier scan : {res['timestamp']} · "
                       f"{res['scanned']} paires · {res['duration']:.1f}s")

    if launch:
        if not sel_chains:
            st.error("Sélectionnez au moins une blockchain.")
        else:
            cfg = {"chains": sel_chains, "min_liq": min_liq,
                   "min_mcap": min_mcap, "max_mcap": max_mcap,
                   "min_mom": min_mom, "min_vol24": DEFAULT_MIN_VOL24,
                   "max_change": max_chg}
            result = run_scan(cfg)
            st.session_state["crypto_result"] = result
            st.rerun()

    # ── Résultats ─────────────────────────────────────────────────────────────
    if "crypto_result" not in st.session_state:
        st.info("Configurez vos filtres dans la barre latérale et lancez le scan.")
        return

    res  = st.session_state["crypto_result"]
    gems = res["gems"]

    # Stats bar
    st.markdown(f"""<div class="stat-bar">
      <div class="stat-item">
        <div class="stat-label">Paires analysées</div>
        <div class="stat-val">{res['scanned']}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">💎 Gems détectés</div>
        <div class="stat-val {'green' if gems else 'red'}">{len(gems)}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Meilleur score</div>
        <div class="stat-val" style="color:#e3b341">
          {gems[0]['score'] if gems else '—'}
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Durée du scan</div>
        <div class="stat-val">{res['duration']:.1f}s</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not gems:
        st.warning("Aucun token ne correspond aux critères actuellement. "
                   "Essayez d'assouplir les filtres ou relancez dans quelques minutes.")
        return

    # Tableau principal
    st.markdown(f"### Top {min(20, len(gems))} Gems détectés")
    st.markdown(render_gem_table(gems), unsafe_allow_html=True)

    st.markdown("---")

    # Détails expandables
    st.markdown("### Fiches détaillées")
    for i, g in enumerate(gems[:10], 1):
        color   = CHAIN_COLORS.get(g["chain"], "#a78bfa")
        mom_pct = min(g["momentum"] / 6.0, 1.0) * 100
        with st.expander(f"#{i} — {g['name']} ({g['symbol']}) · Score {g['score']}"):
            ka, kb, kc, kd = st.columns(4)
            ka.metric("Prix USD",  f"${g['price_usd']}")
            kb.metric("Market Cap", _fmt(g["market_cap"]))
            kc.metric("Liquidité", _fmt(g["liquidity"]))
            kd.metric("Momentum",  f"{g['momentum']}x")

            # Barre momentum
            st.markdown(f"""
<div style="margin:12px 0;padding:14px 16px;background:rgba(7,9,26,0.6);
    border:1px solid rgba(255,255,255,0.05);border-radius:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;
      font-size:11px;color:rgba(139,148,158,0.7);margin-bottom:10px">
    <span style="font-weight:600;text-transform:uppercase;letter-spacing:1.5px;font-size:9px">Momentum volume 6h/24h</span>
    <span style="color:{color};font-weight:800;font-size:14px;font-family:'JetBrains Mono',monospace">{g['momentum']}x</span>
  </div>
  <div style="background:rgba(30,42,58,0.8);border-radius:4px;height:5px;border:1px solid rgba(255,255,255,0.04)">
    <div style="width:{mom_pct:.0f}%;height:100%;border-radius:4px;
        background:linear-gradient(90deg,#00d4aa,#a78bfa);
        box-shadow:0 0 8px rgba(0,212,170,0.35)"></div>
  </div>
</div>""", unsafe_allow_html=True)

            va, vb, vc = st.columns(3)
            va.metric("Var 1h",  f"{g['chg_h1']:+.1f}%")
            vb.metric("Var 6h",  f"{g['chg_h6']:+.1f}%")
            vc.metric("Var 24h", f"{g['chg_h24']:+.1f}%")

            wa, wb, wc = st.columns(3)
            wa.metric("Vol 1h",  _fmt(g["vol_h1"]))
            wb.metric("Vol 6h",  _fmt(g["vol_h6"]))
            wc.metric("Vol 24h", _fmt(g["vol_h24"]))

            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;flex-wrap:wrap;gap:8px">
  <div style="display:flex;align-items:center;gap:10px">
    <span class="badge" style="background:{color}18;color:{color};border:1px solid {color}35">{g['chain']}</span>
    <a href="{g['url']}" target="_blank"
       style="color:#a78bfa;text-decoration:none;border:1px solid rgba(124,58,237,0.3);
       padding:6px 16px;border-radius:9px;font-size:12px;font-weight:600;
       background:rgba(124,58,237,0.07)">
       → Voir sur DexScreener
    </a>
  </div>
  <div style="display:flex;align-items:center;gap:6px">
    <span style="color:rgba(139,148,158,0.6);font-size:11px;text-transform:uppercase;letter-spacing:1px">Score</span>
    <span style="color:#e3b341;font-size:22px;font-weight:900;font-family:'JetBrains Mono',monospace">{g['score']}</span>
  </div>
</div>""", unsafe_allow_html=True)
