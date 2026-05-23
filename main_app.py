"""Dashboard Patrimonial — Point d'entrée unique PEA + Crypto Gems."""

import streamlit as st

st.set_page_config(
    page_title="Dashboard Patrimonial",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS partagé ───────────────────────────────────────────────────────────────

SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ── Base ── */
html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Chrome Streamlit caché ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #050810; }
::-webkit-scrollbar-thumb { background: rgba(0,212,170,0.25); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,170,0.5); }

/* ── Layout ── */
.block-container {
    padding-top: 0 !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 100% !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #07091a 0%, #050810 100%) !important;
    border-right: 1px solid rgba(0,212,170,0.08) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #00d4aa; font-size: 10px; letter-spacing: 2px;
    text-transform: uppercase; font-weight: 700; margin-bottom: 8px;
}

/* ── Onglets ── */
[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-size: 13px !important; font-weight: 600 !important;
    letter-spacing: 0.3px !important; color: rgba(139,148,158,0.8) !important;
    border: none !important; background: transparent !important;
    padding: 12px 20px !important; transition: color 0.2s !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    color: #e6edf3 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e6edf3 !important;
    border-bottom: 2px solid #00d4aa !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    gap: 0 !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: rgba(15,21,32,0.7) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    padding: 16px !important;
    backdrop-filter: blur(10px);
}

/* ── Boutons ── */
button[kind="primary"] {
    background: linear-gradient(135deg, #00d4aa, #00b894) !important;
    border: none !important;
    color: #050810 !important;
    font-weight: 700 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 0 24px rgba(0,212,170,0.25) !important;
    transition: all 0.2s !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 0 36px rgba(0,212,170,0.4) !important;
    transform: translateY(-1px) !important;
}
button[kind="secondary"], button:not([kind]) {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    color: #e6edf3 !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
}
button[kind="secondary"]:hover, button:not([kind]):hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(0,212,170,0.25) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.015) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { font-weight: 600 !important; }

/* ── Couleurs sémantiques ── */
.green  { color: #00d4aa; }
.red    { color: #ff5252; }
.orange { color: #f7931a; }
.purple { color: #a78bfa; }
.blue   { color: #42a5f5; }

/* ── Logo sidebar ── */
.nav-logo {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 26px 4px 12px;
}
.nav-logo-icon {
    width: 42px; height: 42px; border-radius: 12px;
    background: linear-gradient(135deg, rgba(0,212,170,0.12), rgba(167,139,250,0.12));
    border: 1px solid rgba(0,212,170,0.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    box-shadow: 0 0 16px rgba(0,212,170,0.1);
    flex-shrink: 0;
}
.nav-title {
    font-size: 15px; font-weight: 800; letter-spacing: 2.5px;
    background: linear-gradient(90deg, #00d4aa 0%, #a78bfa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}
.nav-sub {
    color: rgba(139,148,158,0.55);
    font-size: 9.5px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 3px;
    font-weight: 500;
}
.glass-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,212,170,0.15), transparent);
    margin: 10px 0 14px;
}

/* ── Barre de stats ── */
.stat-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    background: rgba(7,9,26,0.7);
    border: 1px solid rgba(0,212,170,0.1);
    border-radius: 14px;
    overflow: hidden;
    margin: 16px 0;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.04);
}
.stat-item {
    padding: 18px 22px;
    border-right: 1px solid rgba(255,255,255,0.04);
    text-align: center;
    position: relative;
    transition: background 0.2s;
}
.stat-item:last-child { border-right: none; }
.stat-item:hover { background: rgba(0,212,170,0.025); }
.stat-label {
    color: rgba(139,148,158,0.65);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    font-weight: 700;
}
.stat-val {
    color: #e6edf3;
    font-size: 22px;
    font-weight: 800;
    margin-top: 5px;
    letter-spacing: -0.5px;
}
.stat-sub { font-size: 11px; margin-top: 3px; color: rgba(139,148,158,0.7); }

/* ── Bannière ── */
.radar-banner {
    padding: 30px 0 22px;
    margin-bottom: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    position: relative;
    overflow: hidden;
}
.radar-banner::before {
    content: '';
    position: absolute;
    top: 0; left: -3rem; right: -3rem; height: 120%;
    background: radial-gradient(ellipse 70% 80% at 50% 0%, rgba(0,212,170,0.05), transparent 70%);
    pointer-events: none;
}
.radar-banner h1 {
    font-size: 30px; font-weight: 900; letter-spacing: 3px;
    margin: 0 0 8px 0; line-height: 1.05;
}
.radar-banner p {
    color: rgba(139,148,158,0.6);
    font-size: 12px;
    margin: 0;
    letter-spacing: 0.5px;
    font-weight: 400;
}

/* ── Tableau ── */
.cg-wrap {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.05);
    margin-top: 14px;
    box-shadow: 0 4px 32px rgba(0,0,0,0.2);
}
.cg-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
}
.cg-table thead tr { background: rgba(15,21,32,0.98); }
.cg-table th {
    padding: 12px 16px;
    color: rgba(139,148,158,0.6);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700;
    text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    white-space: nowrap;
}
.cg-table tbody tr {
    background: rgba(7,9,26,0.5);
    transition: background 0.15s;
}
.cg-table tbody tr:nth-child(even) {
    background: rgba(15,21,32,0.6);
}
.cg-table tbody tr:hover td { background: rgba(0,212,170,0.035) !important; }
.cg-table td {
    padding: 13px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.025);
    white-space: nowrap;
}
.cg-table tbody tr:last-child td { border-bottom: none; }
.nom-main {
    font-weight: 700;
    color: #e6edf3;
    font-size: 13px;
    letter-spacing: 0.1px;
}
.nom-sub {
    font-size: 10px;
    color: rgba(139,148,158,0.55);
    margin-top: 2px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.3px;
}
.rank {
    color: rgba(139,148,158,0.4);
    font-size: 11px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Badges ── */
.badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 3px 11px;
    border-radius: 20px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.2px;
    min-width: 44px;
}
.bg {
    background: rgba(0,212,170,0.1);
    color: #00d4aa;
    border: 1px solid rgba(0,212,170,0.22);
    box-shadow: 0 0 10px rgba(0,212,170,0.12);
}
.bo {
    background: rgba(247,147,26,0.1);
    color: #f7931a;
    border: 1px solid rgba(247,147,26,0.22);
    box-shadow: 0 0 10px rgba(247,147,26,0.12);
}
.br {
    background: rgba(255,82,82,0.1);
    color: #ff5252;
    border: 1px solid rgba(255,82,82,0.22);
    box-shadow: 0 0 10px rgba(255,82,82,0.12);
}

/* ── KPI Cards ── */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
    gap: 10px;
    margin-bottom: 22px;
}
.kpi-card {
    background: rgba(7,9,26,0.75);
    border: 1px solid rgba(255,255,255,0.055);
    border-radius: 13px;
    padding: 16px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.2s;
    backdrop-filter: blur(10px);
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00d4aa, #a78bfa);
    opacity: 0.45;
}
.kpi-card:hover {
    border-color: rgba(0,212,170,0.18);
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.25);
}
.kpi-label {
    color: rgba(139,148,158,0.65);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    font-weight: 700;
}
.kpi-val {
    color: #e6edf3;
    font-size: 20px;
    font-weight: 800;
    margin-top: 7px;
    letter-spacing: -0.4px;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 10px;
    margin-top: 4px;
    color: rgba(139,148,158,0.6);
}

/* ── Signal Cards ── */
.sig-card {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: transform 0.15s;
    backdrop-filter: blur(6px);
}
.sig-card:hover { transform: translateX(3px); }

/* ── Crypto Warning ── */
.crypto-warn {
    background: rgba(40,20,20,0.6);
    border: 1px solid rgba(248,81,73,0.2);
    border-left: 3px solid #ff5252;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 18px;
    color: rgba(255,161,152,0.8);
    font-size: 12px;
    line-height: 1.7;
    backdrop-filter: blur(6px);
}

/* ── Animations ── */
@keyframes fade-up {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.stat-bar  { animation: fade-up 0.35s ease-out; }
.kpi-card  { animation: fade-up 0.4s ease-out; }
.cg-wrap   { animation: fade-up 0.45s ease-out; }
.sig-card  { animation: fade-up 0.4s ease-out; }
</style>
"""

st.markdown(SHARED_CSS, unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div class="nav-logo">
  <div class="nav-logo-icon">💎</div>
  <div>
    <div class="nav-title">DASHBOARD</div>
    <div class="nav-sub">Patrimonial · PEA + Crypto</div>
  </div>
</div>
<div class="glass-divider"></div>
""", unsafe_allow_html=True)

    universe = st.radio(
        "Univers",
        ["📈 Radar PEA & Portefeuille", "⚡ Évaluateur Crypto (Gems)"],
        label_visibility="collapsed",
    )
    st.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)

# ── Rendu conditionnel ────────────────────────────────────────────────────────

if "PEA" in universe:
    import pea_tab
    pea_tab.render()
else:
    import crypto_tab
    crypto_tab.render()
