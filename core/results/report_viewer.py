"""
RedTrace — Red Teaming Dashboard
=================================
Streamlit dashboard that provides deep visibility into attack campaigns.

Sections
--------
1. Overview   — KPIs, breach-rate gauge, framework split, timeline
2. Attacks    — filterable list with conversation / probe drill-down
3. Analysis   — turn-level heatmap, technique comparison, scorer insights

Launch:  streamlit run core/results/report_viewer.py
"""

import json
import html
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import streamlit as st

# ── Project root on sys.path so `config` is importable ──────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_runtime_settings

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RedTrace — Attack Dashboard",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stApp"] {
    background-color: #0e1117; color: #c9d1d9;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"], [data-testid="stToolbar"] {
    background-color: #0e1117 !important;
}
[data-testid="stSidebar"] {
    background-color: #161b22 !important; border-right: 1px solid #30363d;
}
[data-testid="stSidebar"] * { color: #8b949e !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {
    color: #c9d1d9 !important;
}
[data-testid="stExpander"] {
    background-color: #161b22; border: 1px solid #30363d; border-radius: 8px;
}

/* ── KPI cards ────────────────────────────────────────────── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
.kpi {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 16px 20px; border-top: 3px solid;
}
.kpi.blue   { border-top-color: #58a6ff; }
.kpi.red    { border-top-color: #f85149; }
.kpi.green  { border-top-color: #3fb950; }
.kpi.orange { border-top-color: #d29922; }
.kpi.purple { border-top-color: #bc8cff; }
.kpi .label {
    font-size: 10px; color: #8b949e; text-transform: uppercase;
    letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;
}
.kpi .value { font-size: 28px; font-weight: 700; color: #f0f6fc; line-height: 1; }
.kpi .sub   { font-size: 11px; color: #484f58; font-family: 'JetBrains Mono', monospace; margin-top: 6px; }

/* ── Breach gauge ─────────────────────────────────────────── */
.gauge-container { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; }
.gauge-bar {
    flex: 1; height: 14px; background: #21262d; border-radius: 7px; overflow: hidden;
    border: 1px solid #30363d;
}
.gauge-fill { height: 100%; border-radius: 7px; transition: width .5s ease; }
.gauge-label {
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
    font-weight: 600; min-width: 56px; text-align: right;
}

/* ── Attack cards ─────────────────────────────────────────── */
.attack-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    margin-bottom: 10px; overflow: hidden;
}
.attack-card.breached { border-left: 4px solid #f85149; }
.attack-card.hardened { border-left: 4px solid #3fb950; }
.attack-header {
    display: flex; align-items: center; gap: 12px; padding: 14px 18px; flex-wrap: wrap;
}
.fw-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;
    padding: 3px 8px; border-radius: 4px; text-transform: uppercase;
}
.fw-pyrit  { background: #1c2333; color: #79c0ff; border: 1px solid #388bfd44; }
.fw-garak  { background: #0d1f0d; color: #56d364; border: 1px solid #3fb95044; }
.outcome-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;
    padding: 3px 9px; border-radius: 4px;
}
.outcome-breached { background: #3d1114; color: #f85149; border: 1px solid #f8514944; }
.outcome-hardened { background: #0d2818; color: #3fb950; border: 1px solid #3fb95044; }
.attack-name {
    font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #c9d1d9; flex: 1;
}
.attack-meta {
    font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #484f58;
}

/* ── Objective ────────────────────────────────────────────── */
.objective-box {
    background: #1c2333; border: 1px solid #388bfd44; border-left: 3px solid #58a6ff;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #79c0ff; line-height: 1.6;
}
.obj-label {
    font-size: 9px; color: #58a6ff; text-transform: uppercase;
    letter-spacing: 1.5px; font-weight: 600; margin-bottom: 6px;
}

/* ── Conversation turns ───────────────────────────────────── */
.turn-block { margin-bottom: 16px; }
.turn-header {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #484f58; margin-bottom: 6px;
}
.msg {
    border-radius: 8px; padding: 12px 14px; margin-bottom: 4px;
    font-family: 'JetBrains Mono', monospace; font-size: 12px;
    line-height: 1.65; white-space: pre-wrap; word-break: break-word;
}
.msg-label {
    font-size: 9px; text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600; margin-bottom: 5px;
}
.msg-attacker { background: #1c1633; border: 1px solid #6e40c966; color: #d2a8ff; }
.msg-attacker .msg-label { color: #bc8cff; }
.msg-target   { background: #0d2818; border: 1px solid #3fb95044; color: #aff5b4; }
.msg-target .msg-label { color: #56d364; }
.msg-empty    { color: #484f58; font-style: italic; }

/* ── Score chips ──────────────────────────────────────────── */
.score-row { display: flex; align-items: flex-start; gap: 8px; margin-top: 6px; }
.score-chip {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;
    padding: 3px 8px; border-radius: 4px; white-space: nowrap; flex-shrink: 0;
}
.chip-leaked { background: #3d1114; color: #f85149; border: 1px solid #f8514944; }
.chip-safe   { background: #0d2818; color: #3fb950; border: 1px solid #3fb95044; }
.chip-nodata { background: #21262d; color: #484f58; border: 1px solid #30363d; }
.rationale {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #8b949e;
    font-style: italic; line-height: 1.5;
}
.summary-line {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    padding: 10px 0 2px 0; border-top: 1px solid #21262d; margin-top: 14px;
}

/* ── Garak probes ─────────────────────────────────────────── */
.garak-probe {
    border: 1px solid #30363d; border-radius: 8px; padding: 14px; margin-bottom: 8px;
    background: #161b22;
}
.garak-probe.fail { border-left: 3px solid #f85149; }
.garak-probe.pass { border-left: 3px solid #3fb950; }
.probe-status {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; margin-bottom: 8px;
}
.probe-status.fail { color: #f85149; }
.probe-status.pass { color: #3fb950; }
.field-label {
    font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #484f58;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; font-weight: 600;
}
.field-value {
    font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #c9d1d9;
    line-height: 1.5; white-space: pre-wrap; word-break: break-word;
}

/* ── Analysis cards ───────────────────────────────────────── */
.analysis-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 20px; margin-bottom: 16px;
}
.analysis-title {
    font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #8b949e;
    text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; margin-bottom: 14px;
}
.stat-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #21262d;
    font-family: 'JetBrains Mono', monospace; font-size: 12px;
}
.stat-label { color: #8b949e; }
.stat-value { color: #f0f6fc; font-weight: 600; }
.bar-track { flex: 1; height: 6px; background: #21262d; border-radius: 3px; margin: 0 12px; }
.bar-fill  { height: 100%; border-radius: 3px; }

.empty {
    text-align: center; padding: 60px; color: #484f58;
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Data helpers
# ═════════════════════════════════════════════════════════════════

def load_reports(reports_path: Path) -> list[dict]:
    """Load all JSON report files, newest first."""
    files = sorted(
        [f for f in os.listdir(reports_path) if f.endswith(".json")],
        reverse=True,
    )
    reports = []
    for filename in files:
        try:
            with open(reports_path / filename, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                data["_filename"] = filename
                reports.append(data)
        except Exception:
            pass
    return reports


def is_breached(r: dict) -> bool:
    conv = r.get("conversation")
    if conv:
        return conv.get("achieved", False)
    prompts = r.get("prompts") or []
    return any(not p.get("passed", True) for p in prompts)


def e(text) -> str:
    """HTML-escape helper."""
    return html.escape(str(text)) if text else ""


def parse_ts(r: dict) -> datetime | None:
    raw = r.get("timestamp", "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════
# KPIs
# ═════════════════════════════════════════════════════════════════

def compute_kpis(reports: list[dict]) -> dict:
    total = len(reports)
    breached = sum(1 for r in reports if is_breached(r))
    hardened = total - breached
    rate = round(breached / total * 100) if total else 0

    total_turns = 0
    leaked_turns = 0
    for r in reports:
        conv = r.get("conversation")
        if conv:
            turns = conv.get("turns", [])
            total_turns += len(turns)
            leaked_turns += sum(1 for t in turns if t.get("score"))

    total_probes = 0
    failed_probes = 0
    for r in reports:
        prompts = r.get("prompts") or []
        total_probes += len(prompts)
        failed_probes += sum(1 for p in prompts if not p.get("passed", True))

    pyrit_count = sum(1 for r in reports if r.get("framework") == "pyrit")
    garak_count = sum(1 for r in reports if r.get("framework") == "garak")

    pyrit_convs = [r for r in reports if r.get("framework") == "pyrit" and r.get("conversation")]
    avg_depth = round(
        sum(len(r["conversation"].get("turns", [])) for r in pyrit_convs) / len(pyrit_convs), 1
    ) if pyrit_convs else 0

    return {
        "total": total, "breached": breached, "hardened": hardened, "rate": rate,
        "turns": total_turns, "leaked_turns": leaked_turns,
        "probes": total_probes, "failed_probes": failed_probes,
        "pyrit": pyrit_count, "garak": garak_count,
        "avg_depth": avg_depth,
    }


def render_kpis(k: dict):
    """Render the top KPI row + breach gauge bar."""
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi blue">
            <div class="label">Total Attacks</div>
            <div class="value">{k['total']}</div>
            <div class="sub">pyrit {k['pyrit']} · garak {k['garak']}</div>
        </div>
        <div class="kpi red">
            <div class="label">Breached</div>
            <div class="value">{k['breached']}</div>
            <div class="sub">{k['rate']}% breach rate</div>
        </div>
        <div class="kpi green">
            <div class="label">Hardened</div>
            <div class="value">{k['hardened']}</div>
            <div class="sub">{100 - k['rate']}% resisted</div>
        </div>
        <div class="kpi orange">
            <div class="label">Conv. Turns</div>
            <div class="value">{k['turns']}</div>
            <div class="sub">{k['leaked_turns']} leaked · avg depth {k['avg_depth']}</div>
        </div>
        <div class="kpi purple">
            <div class="label">Garak Probes</div>
            <div class="value">{k['probes']}</div>
            <div class="sub">{k['failed_probes']} failed</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Breach gauge ──
    rate = k["rate"]
    color = "#3fb950" if rate < 25 else ("#d29922" if rate < 50 else "#f85149")
    st.markdown(f"""
    <div class="gauge-container">
        <span class="gauge-label" style="color:{color}">{rate}%</span>
        <div class="gauge-bar">
            <div class="gauge-fill" style="width:{rate}%; background:{color}"></div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#484f58">
            breach rate
        </span>
    </div>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Analysis tab helpers
# ═════════════════════════════════════════════════════════════════

def render_analysis(reports: list[dict]):
    """Render the Analysis tab with technique breakdown and turn-level insights."""

    col1, col2 = st.columns(2)

    # ── Attack technique breakdown ─────────────────────────────
    with col1:
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        st.markdown('<div class="analysis-title">Attack Technique Breakdown</div>', unsafe_allow_html=True)

        technique_stats: dict[str, dict] = {}
        for r in reports:
            name = r.get("attack_name", "unknown")
            if " - " in name:
                technique = name.split(" - ", 1)[1].split(" | ")[0].strip()
            else:
                technique = name
            if technique not in technique_stats:
                technique_stats[technique] = {"total": 0, "breached": 0}
            technique_stats[technique]["total"] += 1
            if is_breached(r):
                technique_stats[technique]["breached"] += 1

        for tech, stats in sorted(technique_stats.items(), key=lambda x: -x[1]["breached"]):
            pct = round(stats["breached"] / stats["total"] * 100) if stats["total"] else 0
            bar_color = "#f85149" if pct >= 50 else ("#d29922" if pct > 0 else "#3fb950")
            st.markdown(f"""
            <div class="stat-row">
                <span class="stat-label">{e(tech)}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{pct}%;background:{bar_color}"></div>
                </div>
                <span class="stat-value">{stats['breached']}/{stats['total']}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Turn-level leak heatmap (PyRIT only) ───────────────────
    with col2:
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        st.markdown('<div class="analysis-title">Turn-Level Leak Analysis (PyRIT)</div>', unsafe_allow_html=True)

        turn_stats: dict[int, dict] = defaultdict(lambda: {"total": 0, "leaked": 0})
        max_turn = 0
        for r in reports:
            conv = r.get("conversation")
            if not conv:
                continue
            for t in conv.get("turns", []):
                tn = t.get("turn", 0)
                if tn > max_turn:
                    max_turn = tn
                turn_stats[tn]["total"] += 1
                if t.get("score"):
                    turn_stats[tn]["leaked"] += 1

        if turn_stats:
            for tn in range(1, max_turn + 1):
                s = turn_stats.get(tn, {"total": 0, "leaked": 0})
                pct = round(s["leaked"] / s["total"] * 100) if s["total"] else 0
                bar_color = "#f85149" if pct > 0 else "#3fb950"
                st.markdown(f"""
                <div class="stat-row">
                    <span class="stat-label">Turn {tn}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{max(pct, 2)}%;background:{bar_color}"></div>
                    </div>
                    <span class="stat-value">{s['leaked']}/{s['total']} leaked</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#484f58;font-size:12px;text-align:center;padding:20px">No PyRIT conversations yet.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Timeline ───────────────────────────────────────────────
    st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
    st.markdown('<div class="analysis-title">Attack Timeline</div>', unsafe_allow_html=True)

    sorted_reports = sorted(reports, key=lambda r: r.get("timestamp", ""))
    for r in sorted_reports:
        ts = parse_ts(r)
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "?"
        fw = r.get("framework", "?")
        name = r.get("attack_name", "?")
        b = is_breached(r)
        dot_color = "#f85149" if b else "#3fb950"
        outcome_text = "BREACHED" if b else "HARDENED"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid #21262d">
            <span style="width:8px;height:8px;border-radius:50%;background:{dot_color};flex-shrink:0"></span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#484f58;min-width:120px">{ts_str}</span>
            <span class="fw-badge fw-{fw}" style="font-size:9px">{fw.upper()}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#c9d1d9;flex:1">{e(name)}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:{dot_color}">{outcome_text}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Detector breakdown (Garak) ─────────────────────────────
    garak_reports = [r for r in reports if r.get("framework") == "garak"]
    if garak_reports:
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        st.markdown('<div class="analysis-title">Garak Detector Breakdown</div>', unsafe_allow_html=True)
        detector_stats: dict[str, dict] = {}
        for r in garak_reports:
            for p in r.get("prompts") or []:
                det = p.get("detector") or "unknown"
                if det not in detector_stats:
                    detector_stats[det] = {"total": 0, "failed": 0}
                detector_stats[det]["total"] += 1
                if not p.get("passed", True):
                    detector_stats[det]["failed"] += 1

        for det, stats in sorted(detector_stats.items(), key=lambda x: -x[1]["failed"]):
            pct = round(stats["failed"] / stats["total"] * 100) if stats["total"] else 0
            bar_color = "#f85149" if pct >= 50 else ("#d29922" if pct > 0 else "#3fb950")
            st.markdown(f"""
            <div class="stat-row">
                <span class="stat-label">{e(det)}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{max(pct, 2)}%;background:{bar_color}"></div>
                </div>
                <span class="stat-value">{stats['failed']}/{stats['total']} failed</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Attack renderers
# ═════════════════════════════════════════════════════════════════

def render_pyrit(report: dict):
    """Render a PyRIT attack card with expandable conversation trace."""
    conv = report.get("conversation", {})
    achieved = conv.get("achieved", False)
    turns = conv.get("turns", [])
    leaked_turns = sum(1 for t in turns if t.get("score"))

    card_class = "breached" if achieved else "hardened"
    outcome_class = "outcome-breached" if achieved else "outcome-hardened"
    outcome_label = "BREACHED" if achieved else "HARDENED"
    ts = report.get("timestamp", "")[:16].replace("T", " ")

    st.markdown(f"""
    <div class="attack-card {card_class}">
        <div class="attack-header">
            <span class="fw-badge fw-pyrit">PYRIT</span>
            <span class="outcome-badge {outcome_class}">{outcome_label}</span>
            <span class="attack-name">{e(report.get('attack_name', ''))}</span>
            <span class="attack-meta">{len(turns)} turns · {leaked_turns} leaked · {ts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔍 View conversation trace", expanded=False):
        objective = conv.get("objective", "")
        if objective:
            st.markdown(f"""
            <div class="objective-box">
                <div class="obj-label">🎯 Objective</div>
                {e(objective)}
            </div>
            """, unsafe_allow_html=True)

        if not turns:
            st.markdown('<div class="empty">No turns recorded.</div>', unsafe_allow_html=True)
            return

        for turn in turns:
            turn_num = turn.get("turn", "?")
            prompt_text = turn.get("prompt", "")
            response_text = turn.get("response", "")
            score = turn.get("score", False)
            rationale_text = turn.get("rationale", "")

            if not response_text:
                chip = '<span class="score-chip chip-nodata">NO RESPONSE</span>'
            elif score:
                chip = '<span class="score-chip chip-leaked">⚠ LEAKED</span>'
            else:
                chip = '<span class="score-chip chip-safe">✓ SAFE</span>'

            prompt_html = e(prompt_text) if prompt_text else '<span class="msg-empty">— empty —</span>'
            response_html = e(response_text) if response_text else '<span class="msg-empty">— no response —</span>'
            rationale_html = f'<div class="rationale">{e(rationale_text)}</div>' if rationale_text else ''

            st.markdown(f"""
            <div class="turn-block">
                <div class="turn-header">── TURN {turn_num} ──</div>
                <div class="msg msg-attacker">
                    <div class="msg-label">🤖 Attacker</div>
                    {prompt_html}
                </div>
                <div class="msg msg-target">
                    <div class="msg-label">🎯 Target</div>
                    {response_html}
                </div>
                <div class="score-row">
                    {chip}
                    {rationale_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

        summary_color = "#f85149" if achieved else "#3fb950"
        summary_icon = "💥" if achieved else "🛡️"
        summary_label = "Objective achieved — attack succeeded" if achieved else "Objective not achieved — target held"
        st.markdown(f"""
        <div class="summary-line" style="color:{summary_color}">
            {summary_icon} {summary_label}
        </div>
        """, unsafe_allow_html=True)


def render_garak(report: dict):
    """Render a Garak attack card with expandable probe details."""
    prompts = report.get("prompts") or []
    failed = sum(1 for p in prompts if not p.get("passed", True))
    passed_count = len(prompts) - failed
    card_class = "breached" if failed > 0 else "hardened"
    outcome_label = f"{failed} FAILED" if failed > 0 else "ALL PASSED"
    outcome_class = "outcome-breached" if failed > 0 else "outcome-hardened"
    ts = report.get("timestamp", "")[:16].replace("T", " ")

    detectors = set(p.get("detector", "") for p in prompts if p.get("detector"))
    det_str = f" · detectors: {', '.join(sorted(detectors))}" if detectors else ""

    st.markdown(f"""
    <div class="attack-card {card_class}">
        <div class="attack-header">
            <span class="fw-badge fw-garak">GARAK</span>
            <span class="outcome-badge {outcome_class}">{outcome_label}</span>
            <span class="attack-name">{e(report.get('attack_name', ''))}</span>
            <span class="attack-meta">{len(prompts)} probes · {passed_count}✓ {failed}✗ · {ts}{det_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔍 View probes", expanded=False):
        if not prompts:
            st.markdown('<div class="empty">No probes recorded.</div>', unsafe_allow_html=True)
            return

        for idx, p in enumerate(prompts):
            passed_flag = p.get("passed", True)
            row_class = "pass" if passed_flag else "fail"
            status_label = "✓ PASS" if passed_flag else "✗ FAIL"
            score = p.get("score")
            score_str = f" · score {score}" if score is not None else ""
            detector = p.get("detector", "")
            rationale = p.get("rationale", "")

            c1, c2 = st.columns(2)
            with c1:
                detector_html = (
                    f'<div class="field-label" style="margin-top:8px">Detector</div>'
                    f'<div class="field-value">{e(detector)}</div>'
                ) if detector else ""
                st.markdown(f"""
                <div class="garak-probe {row_class}">
                    <div class="probe-status {row_class}">#{idx + 1} {status_label}{score_str}</div>
                    <div class="field-label">Prompt</div>
                    <div class="field-value">{e(p.get('prompt', ''))}</div>
                    {detector_html}
                </div>
                """, unsafe_allow_html=True)
            with c2:
                rationale_html = (
                    f'<div class="field-label" style="margin-top:8px">Rationale</div>'
                    f'<div class="field-value" style="font-style:italic;color:#8b949e">{e(rationale)}</div>'
                ) if rationale else ""
                st.markdown(f"""
                <div class="garak-probe {row_class}">
                    <div class="probe-status {row_class}">Response</div>
                    <div class="field-value">{e(p.get('response', ''))}</div>
                    {rationale_html}
                </div>
                """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════
# Sidebar & filtering
# ═════════════════════════════════════════════════════════════════

def build_sidebar(reports: list[dict]) -> list[dict]:
    """Render sidebar filters and return the filtered list of reports."""
    with st.sidebar:
        st.markdown("## 🔴 RedTrace")
        st.markdown("---")

        st.markdown("**Framework**")
        show_pyrit = st.checkbox("PyRIT", value=True)
        show_garak = st.checkbox("Garak", value=True)

        st.markdown("---")
        st.markdown("**Outcome**")
        show_breached = st.checkbox("Breached", value=True)
        show_hardened = st.checkbox("Hardened", value=True)

        st.markdown("---")
        sort_by = st.selectbox("Sort", ["Latest first", "Oldest first", "Name A→Z"])
        search = st.text_input("🔎 Search", placeholder="attack name, technique...")

        st.markdown("---")
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#484f58">'
            f'{len(reports)} report(s) loaded</div>',
            unsafe_allow_html=True,
        )

    filtered = list(reports)
    if not show_pyrit:
        filtered = [r for r in filtered if r.get("framework") != "pyrit"]
    if not show_garak:
        filtered = [r for r in filtered if r.get("framework") != "garak"]
    if not show_breached:
        filtered = [r for r in filtered if not is_breached(r)]
    if not show_hardened:
        filtered = [r for r in filtered if is_breached(r)]
    if search:
        q = search.lower()
        filtered = [r for r in filtered if q in r.get("attack_name", "").lower()
                     or q in r.get("_filename", "").lower()]
    if sort_by == "Oldest first":
        filtered = list(reversed(filtered))
    elif sort_by == "Name A→Z":
        filtered = sorted(filtered, key=lambda r: r.get("attack_name", ""))

    return filtered


# ═════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════

def main():
    reports_path = Path(get_runtime_settings().json_reports_dir)

    if not reports_path.exists() or not any(reports_path.glob("*.json")):
        st.markdown(
            f'<div class="empty">No reports found in <code>{e(str(reports_path))}</code>'
            f' — run your first attack.</div>',
            unsafe_allow_html=True,
        )
        return

    reports = load_reports(reports_path)
    filtered = build_sidebar(reports)

    # ── Tabs ───────────────────────────────────────────────────
    tab_overview, tab_attacks, tab_analysis = st.tabs(["📊 Overview", "⚔️ Attacks", "🔬 Analysis"])

    # ── TAB 1: Overview ────────────────────────────────────────
    with tab_overview:
        kpis = compute_kpis(reports)
        render_kpis(kpis)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-title">Framework Split</div>', unsafe_allow_html=True)
            for fw, count in [("PyRIT", kpis["pyrit"]), ("Garak", kpis["garak"])]:
                pct = round(count / kpis["total"] * 100) if kpis["total"] else 0
                color = "#58a6ff" if fw == "PyRIT" else "#3fb950"
                st.markdown(f"""
                <div class="stat-row">
                    <span class="stat-label">{fw}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
                    </div>
                    <span class="stat-value">{count} ({pct}%)</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-title">Outcome Split</div>', unsafe_allow_html=True)
            for label, count, color in [
                ("Breached", kpis["breached"], "#f85149"),
                ("Hardened", kpis["hardened"], "#3fb950"),
            ]:
                pct = round(count / kpis["total"] * 100) if kpis["total"] else 0
                st.markdown(f"""
                <div class="stat-row">
                    <span class="stat-label">{label}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
                    </div>
                    <span class="stat-value">{count} ({pct}%)</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-title">Depth & Leaks</div>', unsafe_allow_html=True)
            items = [
                ("Avg conversation depth", f"{kpis['avg_depth']} turns"),
                ("Total turns", str(kpis["turns"])),
                ("Leaked turns", str(kpis["leaked_turns"])),
                ("Total probes (Garak)", str(kpis["probes"])),
                ("Failed probes", str(kpis["failed_probes"])),
            ]
            for label, val in items:
                st.markdown(f"""
                <div class="stat-row">
                    <span class="stat-label">{label}</span>
                    <span class="stat-value">{val}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 2: Attacks ─────────────────────────────────────────
    with tab_attacks:
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#484f58;'
            f'margin-bottom:14px">{len(filtered)} attack(s) displayed</div>',
            unsafe_allow_html=True,
        )
        for report in filtered:
            fw = report.get("framework", "")
            if fw == "pyrit":
                render_pyrit(report)
            elif fw == "garak":
                render_garak(report)
            else:
                st.markdown(
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;'
                    f'color:#484f58;padding:10px">Unknown format: {e(report.get("_filename", ""))}</div>',
                    unsafe_allow_html=True,
                )

    # ── TAB 3: Analysis ────────────────────────────────────────
    with tab_analysis:
        render_analysis(reports)


if __name__ == "__main__":
    main()

