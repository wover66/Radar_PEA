"""Onglet PEA — Classement GARP, Fiche Détaillée, Portefeuille."""

import html
import json
import os
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

from analyzer import run_analysis
from portfolio import (load_portfolio, save_portfolio, add_position,
                       remove_position, enrich_portfolio, portfolio_metrics,
                       get_signals, simulate_buy, MAX_SECTOR_PCT, MAX_COUNTRY_PCT)

COUNTRY_FLAGS = {
    "France":    ("🇫🇷","FR"), "Allemagne": ("🇩🇪","DE"),
    "Pays-Bas":  ("🇳🇱","NL"), "Espagne":   ("🇪🇸","ES"),
    "Italie":    ("🇮🇹","IT"), "Belgique":  ("🇧🇪","BE"),
    "Danemark":  ("🇩🇰","DK"), "Suède":     ("🇸🇪","SE"),
    "Finlande":  ("🇫🇮","FI"), "Norvège":   ("🇳🇴","NO"),
    "Portugal":  ("🇵🇹","PT"), "Irlande":   ("🇮🇪","IE"),
    "Autriche":  ("🇦🇹","AT"), "Autre":     ("🌍","EU"),
}

PIE_PALETTE = ["#00d4aa","#42a5f5","#f7931a","#ce93d8","#ef5350",
               "#66bb6a","#ffa726","#26c6da","#7e57c2","#ec407a",
               "#80cbc4","#a5d6a7","#ffe082","#b0bec5","#ff8a65"]

SIGNAL_COLORS = {
    "🔴 VENDRE": "#ff5252", "🔴 ALLÉGER": "#ff5252",
    "⚠️ SURVEILLER": "#f7931a", "🟡 SURVEILLER": "#f7931a",
    "🟢 RENFORCER": "#00d4aa", "🟢 POINT D'ENTRÉE": "#00d4aa",
    "🔵 CONSERVER": "#42a5f5",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _v(val):
    return val if val is not None and str(val) not in ("nan","None","") else None

def fmt_var(v):
    v = _v(v)
    if v is None: return '<span style="color:#555">—</span>'
    arrow = "▲" if v >= 0 else "▼"
    cls   = "green" if v >= 0 else "red"
    sign  = "+" if v >= 0 else ""
    return f'<span class="{cls}" style="font-weight:600">{arrow} {sign}{v:.2f}%</span>'

def fmt_rsi(rsi):
    rsi = _v(rsi)
    if rsi is None: return '<span style="color:#555">—</span>'
    if rsi > 70: return f'<span class="red">🔴 {rsi:.1f}</span>'
    if rsi < 30: return f'<span class="green">🟢 {rsi:.1f}</span>'
    return f'<span style="color:#c9d1d9">{rsi:.1f}</span>'

def fmt_beta(beta):
    beta = _v(beta)
    if beta is None: return '<span style="color:#555">—</span>'
    cls = 'class="orange"' if beta > 1.5 else 'style="color:#c9d1d9"'
    pfx = "⚠️ " if beta > 1.5 else ""
    return f'<span {cls}>{pfx}{beta:.2f}</span>'

def fmt_num(val, fmt=".1f", suffix=""):
    v = _v(val)
    return f"{v:{fmt}}{suffix}" if v is not None else "—"

def badge(score):
    score = _v(score) or 0
    cls = "bg" if score >= 70 else "bo" if score >= 40 else "br"
    return f'<span class="badge {cls}">{score:.0f}</span>'

def country_cell(pays):
    flag, code = COUNTRY_FLAGS.get(pays, ("🌍","EU"))
    return f'{flag} <span style="color:#8b949e;font-size:11px">{code}</span>'


# ── Données ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600 * 23, show_spinner=False)
def load_data(force: bool = False) -> pd.DataFrame:
    bar = st.progress(0, text="Chargement de l'univers PEA…")
    msg = st.empty()
    def cb(pct, label):
        bar.progress(min(pct, 1.0), text=label)
        msg.caption(label)
    df = run_analysis(force=force, progress_cb=cb)
    bar.empty(); msg.empty()
    return df

@st.cache_data(ttl=3600 * 23, show_spinner=False)
def load_hist(ticker: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period="300d")


# ── Graphique TradingView ─────────────────────────────────────────────────────

def calc_rsi_series(closes, period=14):
    delta = closes.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def make_tv_chart(hist: pd.DataFrame, currency: str) -> go.Figure:
    mm50  = hist["Close"].rolling(50).mean()
    mm200 = hist["Close"].rolling(200).mean()
    rsi   = calc_rsi_series(hist["Close"])
    vol_colors = [
        "#00d4aa" if hist["Close"].iloc[i] >= hist["Open"].iloc[i] else "#ff5252"
        for i in range(len(hist))
    ]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.60, 0.18, 0.22], vertical_spacing=0.02)
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"], name="Prix",
        increasing=dict(line=dict(color="#00d4aa"), fillcolor="#00d4aa"),
        decreasing=dict(line=dict(color="#ff5252"), fillcolor="#ff5252"),
        showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=mm50,  name="MM50",
        line=dict(color="#f7931a", width=1.3, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=mm200, name="MM200",
        line=dict(color="#ef5350", width=1.8)), row=1, col=1)
    fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume",
        marker_color=vol_colors, opacity=0.65, showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=rsi, name="RSI (14)",
        line=dict(color="#ce93d8", width=1.5)), row=3, col=1)
    fig.add_hrect(y0=70, y1=100, row=3, col=1,
                  fillcolor="rgba(255,82,82,0.08)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  row=3, col=1,
                  fillcolor="rgba(0,212,170,0.08)", line_width=0)
    for level, color in [(70,"rgba(255,82,82,0.6)"), (30,"rgba(0,212,170,0.6)")]:
        fig.add_hline(y=level, line_dash="dot", line_color=color,
                      line_width=1, row=3, col=1)
    axis = dict(gridcolor="#1e2a3a", zerolinecolor="#1e2a3a", showgrid=True)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0a0e1a",
        plot_bgcolor="#131722", height=680,
        margin=dict(l=0,r=0,t=10,b=0), xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"))
    fig.update_yaxes(title_text=f"Prix ({currency})", row=1, col=1, **axis)
    fig.update_yaxes(title_text="Vol.",  row=2, col=1, **axis)
    fig.update_yaxes(title_text="RSI",   row=3, col=1, range=[0,100], **axis)
    fig.update_xaxes(**axis)
    return fig


# ── Tableaux HTML ─────────────────────────────────────────────────────────────

def render_table(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        per  = _v(r.get("PER")); de = _v(r.get("D/E"))
        rows.append(f"""<tr>
          <td class="rank">{r['#']}</td>
          <td><div class="nom-main">{html.escape(str(r['Nom']))}</div>
              <div class="nom-sub">{r['Ticker']}</div></td>
          <td>{country_cell(r['Pays'])}</td>
          <td style="color:#8b949e;font-size:11px">{html.escape(str(r['Secteur'])[:22])}</td>
          <td style="font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace">{r['Prix']:.2f}
              <span style="color:rgba(139,148,158,0.5);font-size:10px;font-family:'Inter',sans-serif"> {r['Devise']}</span></td>
          <td>{fmt_var(r.get('Var 1J %'))}</td>
          <td>{fmt_var(r.get('Var 1S %'))}</td>
          <td>{badge(r['Score Total'])}</td>
          <td style="font-size:12px;color:rgba(139,148,158,0.7)">
              <span style="color:#42a5f5;font-weight:600">{r['Score Fond.']}</span>
              <span style="color:rgba(139,148,158,0.3)"> + </span>
              <span style="color:#f7931a;font-weight:600">{r['Score Tech.']}</span></td>
          <td style="font-size:12px">{fmt_rsi(r.get('RSI'))}</td>
          <td style="font-size:12px">{fmt_beta(r.get('Beta'))}</td>
          <td style="font-size:12px;color:#c9d1d9;font-family:'JetBrains Mono',monospace">{f"{per:.1f}" if per else "—"}</td>
          <td style="font-size:12px;color:#c9d1d9;font-family:'JetBrains Mono',monospace">{f"{de:.2f}" if de else "—"}</td>
        </tr>""")
    return f"""<div class="cg-wrap"><table class="cg-table">
  <thead><tr><th>#</th><th>Nom</th><th>Pays</th><th>Secteur</th>
  <th>Prix</th><th>Var 1J</th><th>Var 1S</th>
  <th>Score</th><th>Fond · Tech</th><th>RSI</th><th>Bêta</th><th>PER</th><th>D/E</th>
  </tr></thead><tbody>{"".join(rows)}</tbody></table></div>"""


def render_portfolio_table(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        pnl_pct = _v(r.get("P&L %")); pnl_eur = _v(r.get("P&L €"))
        prix = _v(r.get("Prix")); score = _v(r.get("Score Total"))
        pnl_html = fmt_var(pnl_pct) if pnl_pct is not None else "—"
        pnl_abs = (f'<span style="color:{"#00d4aa" if pnl_eur and pnl_eur>=0 else "#ff5252"}">'
                   f'{"+" if pnl_eur and pnl_eur>=0 else ""}{pnl_eur:,.0f} €</span>'
                   if pnl_eur is not None else "—")
        rows.append(f"""<tr>
          <td><div class="nom-main">{html.escape(str(r['name']))}</div>
              <div class="nom-sub">{r['ticker']}</div></td>
          <td style="text-align:right;color:#e6edf3;font-family:'JetBrains Mono',monospace">{r['quantity']:.2f}</td>
          <td style="text-align:right;color:rgba(139,148,158,0.7);font-family:'JetBrains Mono',monospace">{r['pru']:.2f}</td>
          <td style="text-align:right;font-weight:700;color:#e6edf3;font-family:'JetBrains Mono',monospace">{f"{prix:.2f}" if prix else "—"}</td>
          <td style="text-align:right">{pnl_html}</td>
          <td style="text-align:right">{pnl_abs}</td>
          <td style="text-align:right;font-weight:700;color:#e6edf3">{r.get('Valeur actuelle',0):,.0f} €</td>
          <td style="text-align:right;color:#8b949e">{r.get('Poids %',0):.1f}%</td>
          <td style="text-align:center">{badge(score) if score else "—"}</td>
          <td style="text-align:center">{fmt_rsi(r.get('RSI'))}</td>
        </tr>""")
    return f"""<div class="cg-wrap"><table class="cg-table">
  <thead><tr><th>Valeur</th><th style="text-align:right">Qté</th>
  <th style="text-align:right">PRU</th><th style="text-align:right">Prix</th>
  <th style="text-align:right">P&L %</th><th style="text-align:right">P&L €</th>
  <th style="text-align:right">Valeur</th><th style="text-align:right">Poids</th>
  <th style="text-align:center">Score</th><th style="text-align:center">RSI</th>
  </tr></thead><tbody>{"".join(rows)}</tbody></table></div>"""


# ── Composants portefeuille ────────────────────────────────────────────────────

def donut(labels, values, title):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55, textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        marker=dict(colors=PIE_PALETTE[:len(labels)],
                    line=dict(color="#0a0e1a", width=2)),
        textfont=dict(size=10, color="#fff"),
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title, font=dict(size=13, color="#8b949e"), x=0.5),
        legend=dict(font=dict(size=10, color="#c9d1d9"), bgcolor="rgba(0,0,0,0)"),
        height=290, margin=dict(l=0,r=0,t=36,b=0),
    )
    return fig


def signal_card(sig):
    color = SIGNAL_COLORS.get(sig["kind"], "#8b949e")
    return (f'<div class="sig-card" style="background:{color}18;'
            f'border:1px solid {color}40;border-left:4px solid {color};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div><span style="font-weight:700;color:#e6edf3">{html.escape(str(sig["name"]))}</span>'
            f'<span style="color:#8b949e;font-size:11px;margin-left:8px">{sig["ticker"]}</span></div>'
            f'<span style="color:{color};font-weight:700">{sig["kind"]}</span></div>'
            f'<div style="color:#8b949e;font-size:12px;margin-top:5px">{sig["reason"]}</div></div>')


def bar_chart(data, title, max_x):
    colors = ["#00d4aa" if v >= max_x * 0.6 else "#f7931a" if v >= max_x * 0.3
              else "#ff5252" for v in data.values()]
    fig = go.Figure(go.Bar(
        x=list(data.values()), y=list(data.keys()), orientation="h",
        marker_color=colors, text=[f"{v} pts" for v in data.values()],
        textposition="outside",
    ))
    fig.update_layout(
        template="plotly_dark", title=title,
        paper_bgcolor="#131722", plot_bgcolor="#131722",
        height=230, margin=dict(l=0,r=50,t=35,b=0),
        xaxis=dict(range=[0, max_x + 2], gridcolor="#1e2a3a"),
        yaxis=dict(gridcolor="#1e2a3a"), font=dict(size=12),
    )
    return fig


# ── Render principal ──────────────────────────────────────────────────────────

def render():
    # ── Sidebar PEA ───────────────────────────────────────────────────────────
    with st.sidebar:
        if st.button("🔄 Rafraîchir les données", use_container_width=True):
            st.cache_data.clear(); st.rerun()

        cache_file = os.path.join(os.path.dirname(__file__), "cache.json")
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                ts = json.load(f).get("timestamp","")
            if ts:
                st.caption(f"Données du {datetime.fromisoformat(ts).strftime('%d/%m/%Y %H:%M')}")

        df_full = load_data()

        with st.expander("🔬 Filtres Fondamentaux", expanded=True):
            pays_list   = sorted(df_full["Pays"].dropna().unique())
            sect_list   = sorted(df_full["Secteur"].dropna().unique())
            taille_list = sorted(df_full["Taille"].dropna().unique())
            sel_pays    = st.multiselect("Pays",    pays_list,   default=pays_list)
            sel_sect    = st.multiselect("Secteur", sect_list,   default=sect_list)
            sel_taille  = st.multiselect("Taille",  taille_list, default=taille_list)
            min_score   = st.slider("Score minimum", 0, 100, 0)

        with st.expander("📈 Filtres Techniques", expanded=True):
            hide_rsi  = st.checkbox("Masquer RSI > 70", value=False)
            hide_vol  = st.checkbox("Masquer β > 1.5",  value=False)
            min_mm200 = st.slider("% au-dessus MM200 minimum", -20, 20, -20)

    # ── Filtrage ──────────────────────────────────────────────────────────────
    df = df_full.copy()
    df = df[df["Pays"].isin(sel_pays)]
    df = df[df["Secteur"].isin(sel_sect)]
    df = df[df["Taille"].isin(sel_taille)]
    df = df[df["Score Total"] >= min_score]
    if min_mm200 > -20:
        df = df[df["% MM200"].fillna(-999) >= min_mm200]
    if hide_rsi:
        df = df[~df["Alertes"].str.contains("RSI", na=False)]
    if hide_vol:
        df = df[~df["Alertes"].str.contains("Vol", na=False)]
    df = df.sort_values("Score Total", ascending=False).reset_index(drop=True)
    df["#"] = df.index + 1

    # ── Bannière ──────────────────────────────────────────────────────────────
    st.markdown("""<div class="radar-banner">
      <h1 style="background:linear-gradient(90deg,#00d4aa 0%,#42a5f5 60%,#a78bfa 100%);
         -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
         📈 RADAR PEA</h1>
      <p>Univers européen &nbsp;·&nbsp; Stratégie GARP &nbsp;·&nbsp; Score Fondamental + Technique</p>
    </div>""", unsafe_allow_html=True)

    # ── Stats globales ────────────────────────────────────────────────────────
    d1d = df_full.dropna(subset=["Var 1J %"])
    best_row  = d1d.loc[d1d["Var 1J %"].idxmax()] if not d1d.empty else None
    worst_row = d1d.loc[d1d["Var 1J %"].idxmin()] if not d1d.empty else None
    avg_score = df_full["Score Total"].mean()
    score_cls = "green" if avg_score >= 55 else "orange" if avg_score >= 35 else "red"
    best_html = (f'<div class="stat-val green">▲ {best_row["Var 1J %"]:+.2f}%</div>'
                 f'<div class="stat-sub green">{best_row["Ticker"]}</div>'
                 if best_row is not None else '<div class="stat-val">—</div>')
    worst_html = (f'<div class="stat-val red">▼ {worst_row["Var 1J %"]:+.2f}%</div>'
                  f'<div class="stat-sub red">{worst_row["Ticker"]}</div>'
                  if worst_row is not None else '<div class="stat-val">—</div>')
    st.markdown(f"""<div class="stat-bar">
      <div class="stat-item">
        <div class="stat-label">Valeurs analysées</div>
        <div class="stat-val">{len(df_full)}</div>
        <div class="stat-sub" style="color:#8b949e">{len(df)} affichées</div>
      </div>
      <div class="stat-item"><div class="stat-label">🏆 Meilleure séance</div>{best_html}</div>
      <div class="stat-item"><div class="stat-label">📉 Pire séance</div>{worst_html}</div>
      <div class="stat-item">
        <div class="stat-label">Indice GARP moyen</div>
        <div class="stat-val {score_cls}">{avg_score:.1f}
          <span style="font-size:14px;color:#8b949e">/100</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Onglets PEA ───────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📊  Classement", "🔍  Fiche Détaillée", "💼  Mon Portefeuille"])

    # ── TAB 1 : Classement ────────────────────────────────────────────────────
    with tab1:
        if df.empty:
            st.warning("Aucune valeur ne correspond aux filtres sélectionnés.")
        else:
            st.markdown(render_table(df), unsafe_allow_html=True)
            st.markdown("---")
            st.caption("**Score** = 50 pts fondamentaux (PER sectoriel, D/E, dividende, "
                       "croissance) + 50 pts techniques (MM200 · MM50 · RSI · Volume)  "
                       "· 🔴 RSI>70 (surachat) · ⚠️ Bêta>1.5 (haute volatilité)")

    # ── TAB 2 : Fiche Détaillée ────────────────────────────────────────────────
    with tab2:
        if df_full.empty:
            st.info("Aucune donnée disponible.")
        else:
            choice = st.selectbox("Sélectionner une valeur", df_full["Nom"].tolist())
            row    = df_full[df_full["Nom"] == choice].iloc[0]
            ticker = row["Ticker"]
            st.markdown(f"### {html.escape(choice)}&nbsp; `{ticker}`")

            score_cls2 = "green" if row["Score Total"] >= 70 else \
                         "orange" if row["Score Total"] >= 40 else "red"
            v1d = _v(row.get("Var 1J %"))
            v1s = _v(row.get("Var 1S %"))
            v1d_html = (f'<span class="{"green" if v1d and v1d>=0 else "red"}">'
                        f'{f"{v1d:+.2f}%" if v1d is not None else "—"}</span>')
            v1s_html = (f'<span class="{"green" if v1s and v1s>=0 else "red"}">'
                        f'{f"{v1s:+.2f}%" if v1s is not None else "—"}</span>')
            rsi_val = _v(row.get("RSI"))
            rsi_cls = "red" if rsi_val and rsi_val > 70 else \
                      "green" if rsi_val and rsi_val < 30 else ""
            beta_val = _v(row.get("Beta"))

            st.markdown(f"""<div class="kpi-row">
  <div class="kpi-card"><div class="kpi-label">Score GARP</div>
    <div class="kpi-val {score_cls2}">{row['Score Total']:.0f}
      <span style="font-size:14px;color:#555">/100</span></div>
    <div class="kpi-sub" style="color:#8b949e">Fond.{row['Score Fond.']} · Tech.{row['Score Tech.']}</div>
  </div>
  <div class="kpi-card"><div class="kpi-label">Prix</div>
    <div class="kpi-val">{row['Prix']:.2f}</div>
    <div class="kpi-sub" style="color:#8b949e">{row['Devise']}</div></div>
  <div class="kpi-card"><div class="kpi-label">Var 1 jour</div>
    <div class="kpi-val">{v1d_html}</div></div>
  <div class="kpi-card"><div class="kpi-label">Var 1 semaine</div>
    <div class="kpi-val">{v1s_html}</div></div>
  <div class="kpi-card"><div class="kpi-label">RSI (14j)</div>
    <div class="kpi-val {rsi_cls}">{f"{rsi_val:.1f}" if rsi_val else "—"}</div></div>
  <div class="kpi-card"><div class="kpi-label">PER · Moy. sect.</div>
    <div class="kpi-val">{fmt_num(row.get('PER'))}</div>
    <div class="kpi-sub" style="color:#8b949e">Moy: {row.get('PER Secteur','—')}</div></div>
  <div class="kpi-card"><div class="kpi-label">Dividende</div>
    <div class="kpi-val green">{fmt_num(row.get('Div %'),'.2f','%')}</div></div>
  <div class="kpi-card"><div class="kpi-label">Bêta</div>
    <div class="kpi-val {'orange' if beta_val and beta_val>1.5 else ''}">{fmt_num(row.get('Beta'),'.2f')}</div></div>
</div>""", unsafe_allow_html=True)

            if row.get("Alertes"):
                st.warning(f"⚠️ Alertes : {row['Alertes']}")

            with st.spinner("Chargement du graphique…"):
                hist = load_hist(ticker)
            if not hist.empty:
                st.plotly_chart(make_tv_chart(hist, str(row["Devise"])),
                                use_container_width=True)
            else:
                st.warning("Historique indisponible.")

            st.markdown("---")
            col_f, col_t = st.columns(2)
            with col_f:
                st.plotly_chart(bar_chart(row["_fb"], "Fondamental (50 pts)", 20),
                                use_container_width=True)
                p200 = _v(row.get("% MM200"))
                st.markdown(f"""| | Valeur | Référence |
|---|---|---|
| **PER** | {fmt_num(row.get('PER'),'.1f')} | Moy. sect. {row.get('PER Secteur','—')} |
| **D/E** | {fmt_num(row.get('D/E'),'.2f')} | — |
| **Croiss. CA** | {fmt_num(row.get('Croiss. CA %'),'.1f','%')} | — |
| **Croiss. BNC** | {fmt_num(row.get('Croiss. BNC %'),'.1f','%')} | — |""")
            with col_t:
                st.plotly_chart(bar_chart(row["_tb"], "Technique (50 pts)", 15),
                                use_container_width=True)
                st.markdown(f"""| | Valeur |
|---|---|
| **MM50** | {fmt_num(row.get('MM50'),'.2f')} |
| **MM200** | {fmt_num(row.get('MM200'),'.2f')} |
| **% vs MM200** | {f'{p200:+.1f}%' if p200 is not None else '—'} |
| **Vol Ratio** | {fmt_num(row.get('Vol Ratio'),'.2f')} |""")

    # ── TAB 3 : Portefeuille ──────────────────────────────────────────────────
    with tab3:
        st.header("💼 Mon Portefeuille PEA")
        positions = load_portfolio()

        with st.expander("➕ Ajouter / Modifier une position",
                         expanded=not bool(positions)):
            with st.form("form_add", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1: selected = st.selectbox("Action", df_full["Nom"].tolist())
                with c2: qty = st.number_input("Quantité", min_value=0.01, value=1.0, step=1.0)
                with c3: pru_input = st.number_input("PRU", min_value=0.01,
                                                      value=100.0, step=0.5, format="%.2f")
                with c4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("✅ Ajouter", use_container_width=True)
                if submitted:
                    r = df_full[df_full["Nom"] == selected].iloc[0]
                    positions = add_position(positions, r["Ticker"], selected, qty, pru_input)
                    save_portfolio(positions); st.success(f"**{selected}** ajouté."); st.rerun()

        if positions:
            with st.expander("🗑️ Supprimer une position"):
                to_del = st.selectbox("Position", [p["name"] for p in positions], key="del")
                if st.button("Supprimer", type="secondary"):
                    tick_del = next(p["ticker"] for p in positions if p["name"] == to_del)
                    positions = remove_position(positions, tick_del)
                    save_portfolio(positions); st.rerun()

        st.markdown("---")
        if not positions:
            st.info("Aucune position. Ajoutez vos actions ci-dessus."); return

        enriched = enrich_portfolio(positions, df_full)
        metrics  = portfolio_metrics(enriched)
        pnl_cls  = "green" if metrics["total_pnl"] >= 0 else "red"
        pnl_sign = "+" if metrics["total_pnl"] >= 0 else ""
        score_cls3 = "green" if metrics["garp_score"] >= 65 else \
                     "orange" if metrics["garp_score"] >= 45 else "red"

        st.markdown(f"""<div class="stat-bar">
  <div class="stat-item"><div class="stat-label">Valeur portefeuille</div>
    <div class="stat-val">{metrics['total_value']:,.0f} €</div>
    <div class="stat-sub" style="color:#8b949e">Investi : {metrics['total_invested']:,.0f} €</div></div>
  <div class="stat-item"><div class="stat-label">P&L total</div>
    <div class="stat-val {pnl_cls}">{pnl_sign}{metrics['total_pnl']:,.0f} €</div>
    <div class="stat-sub {pnl_cls}">{pnl_sign}{metrics['total_pnl_pct']:.2f}%</div></div>
  <div class="stat-item"><div class="stat-label">Score GARP pondéré</div>
    <div class="stat-val {score_cls3}">{metrics['garp_score']:.1f}
      <span style="font-size:14px;color:#555">/100</span></div></div>
  <div class="stat-item"><div class="stat-label">Positions</div>
    <div class="stat-val">{metrics['n_positions']}</div></div>
</div>""", unsafe_allow_html=True)

        st.markdown("### Positions actuelles")
        st.markdown(render_portfolio_table(enriched), unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("### Diversification")
        pc1, pc2 = st.columns(2)
        sector_alloc  = enriched.groupby("Secteur")["Poids %"].sum().sort_values(ascending=False)
        country_alloc = enriched.groupby("Pays")["Poids %"].sum().sort_values(ascending=False)
        with pc1:
            st.plotly_chart(donut(sector_alloc.index.tolist(),
                                  sector_alloc.values.tolist(), "Par Secteur"),
                            use_container_width=True)
            for s, pct in sector_alloc.items():
                if pct > MAX_SECTOR_PCT:
                    st.warning(f"⚠️ **{s}** → {pct:.1f}% (seuil : {MAX_SECTOR_PCT}%)")
        with pc2:
            st.plotly_chart(donut(country_alloc.index.tolist(),
                                  country_alloc.values.tolist(), "Par Pays"),
                            use_container_width=True)
            for c, pct in country_alloc.items():
                if pct > MAX_COUNTRY_PCT:
                    st.warning(f"⚠️ **{c}** → {pct:.1f}% (seuil : {MAX_COUNTRY_PCT}%)")

        st.markdown("---")
        st.markdown("### Conseils d'arbitrage")
        signals = get_signals(enriched)
        st.markdown("".join(signal_card(s) for s in signals), unsafe_allow_html=True)
        st.markdown("---")

        with st.expander("🔮 Simulateur What-If", expanded=False):
            s1, s2, s3 = st.columns([3, 1, 1])
            with s1: sim_name = st.selectbox("Simuler l'achat de",
                                              df_full["Nom"].tolist(), key="wif")
            with s2: sim_qty = st.number_input("Quantité", min_value=1, value=10, key="wifq")
            with s3:
                sim_r = df_full[df_full["Nom"] == sim_name].iloc[0]
                sim_price = _v(sim_r.get("Prix")) or 0.0
                st.metric("Prix actuel", f"{sim_price:.2f} {sim_r.get('Devise','')}")

            st.caption(f"Coût estimé : **{sim_qty * sim_price:,.0f} {sim_r.get('Devise','')}**")
            result = simulate_buy(positions, df_full, sim_r["Ticker"],
                                  sim_name, sim_qty, sim_price)
            sim_m  = result["metrics"]
            delta_score = sim_m["garp_score"] - metrics["garp_score"]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Score GARP", f"{sim_m['garp_score']:.1f}/100",
                      delta=f"{delta_score:+.1f}", delta_color="normal")
            m2.metric("Valeur simulée", f"{sim_m['total_value']:,.0f} €",
                      delta=f"+{sim_qty * sim_price:,.0f} €")
            m3.metric("Positions", sim_m["n_positions"],
                      delta=f"+{sim_m['n_positions'] - metrics['n_positions']}")
            sim_sa = result["sector_alloc"]
            top_s  = sim_sa.index[0] if not sim_sa.empty else "—"
            m4.metric("Top secteur simulé", top_s,
                      delta=f"{sim_sa.iloc[0]:.1f}%" if not sim_sa.empty else "")

            for w in result["warnings"]:
                st.warning(f"⚠️ {w}")
            if not result["warnings"]:
                st.success("✅ Aucune concentration excessive détectée.")

            sp1, sp2 = st.columns(2)
            with sp1:
                st.plotly_chart(donut(result["sector_alloc"].index.tolist(),
                                      result["sector_alloc"].values.tolist(),
                                      "Secteurs (simulé)"), use_container_width=True)
            with sp2:
                st.plotly_chart(donut(result["country_alloc"].index.tolist(),
                                      result["country_alloc"].values.tolist(),
                                      "Pays (simulé)"), use_container_width=True)
