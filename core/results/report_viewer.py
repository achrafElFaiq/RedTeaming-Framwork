import streamlit as st
import json
import os
import html
from pathlib import Path

st.set_page_config(
    page_title="RedTrace",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stApp"] {
    background-color: #f5f5f5;
    color: #1a1a1a;
    font-family: 'Inter', sans-serif;
}

/* Fix the white/dark header bar */
[data-testid="stHeader"] {
    background-color: #f5f5f5 !important;
    border-bottom: 1px solid #e0e0e0;
}
[data-testid="stToolbar"] {
    background-color: #f5f5f5 !important;
}

[data-testid="stSidebar"] { background-color: #ebebeb !important; border-right: 1px solid #d0d0d0; }
[data-testid="stSidebar"] * { color: #555 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label { color: #222 !important; }

/* Expander */
[data-testid="stExpander"] { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; }

.kpi-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 24px; }
.kpi { background:#ffffff; border:1px solid #ddd; border-radius:8px; padding:14px 18px; border-top: 2px solid; }
.kpi.blue { border-top-color: #2b7de9; }
.kpi.red { border-top-color: #c0392b; }
.kpi.green { border-top-color: #27ae60; }
.kpi.orange { border-top-color: #e67e22; }
.kpi .label { font-size:10px; color:#999; text-transform:uppercase; letter-spacing:1px; font-family:'JetBrains Mono',monospace; margin-bottom:6px; }
.kpi .value { font-size:26px; font-weight:700; color:#111; line-height:1; }
.kpi .sub { font-size:11px; color:#bbb; font-family:'JetBrains Mono',monospace; margin-top:5px; }

.attack-card { background:#ffffff; border:1px solid #ddd; border-radius:8px; margin-bottom:8px; overflow:hidden; }
.attack-card.breached { border-left: 3px solid #c0392b; }
.attack-card.hardened { border-left: 3px solid #27ae60; }
.attack-header { display:flex; align-items:center; gap:12px; padding:12px 16px; }
.fw-badge { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; padding:2px 7px; border-radius:3px; text-transform:uppercase; }
.fw-pyrit { background:#eef0ff; color:#3730a3; border:1px solid #c7d2fe; }
.fw-garak { background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; }
.outcome-badge { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; padding:2px 8px; border-radius:3px; }
.outcome-breached { background:#fef2f2; color:#b91c1c; border:1px solid #fca5a5; }
.outcome-hardened { background:#f0fdf4; color:#15803d; border:1px solid #86efac; }
.attack-name { font-family:'JetBrains Mono',monospace; font-size:12px; color:#444; flex:1; }
.attack-meta { font-family:'JetBrains Mono',monospace; font-size:11px; color:#aaa; }

.objective-box {
    background:#f8f8ff; border:1px solid #c7d2fe; border-left:3px solid #4c51bf;
    border-radius:6px; padding:10px 14px; margin-bottom:16px;
    font-family:'JetBrains Mono',monospace; font-size:12px; color:#4338ca; line-height:1.6;
}
.obj-label { font-size:9px; color:#4c51bf; text-transform:uppercase; letter-spacing:1.5px; font-weight:600; margin-bottom:5px; }

.turn-block { margin-bottom:14px; }
.turn-header { font-family:'JetBrains Mono',monospace; font-size:10px; color:#bbb; margin-bottom:6px; }
.msg { border-radius:6px; padding:10px 13px; margin-bottom:4px; font-family:'JetBrains Mono',monospace; font-size:12px; line-height:1.6; white-space:pre-wrap; word-break:break-word; }
.msg-label { font-size:9px; text-transform:uppercase; letter-spacing:1px; font-weight:600; margin-bottom:5px; }
.msg-attacker { background:#f5f3ff; border:1px solid #ddd6fe; color:#4c1d95; }
.msg-attacker .msg-label { color:#6d28d9; }
.msg-target { background:#f0fdf4; border:1px solid #bbf7d0; color:#14532d; }
.msg-target .msg-label { color:#16a34a; }
.msg-empty { color:#ccc; font-style:italic; }

.score-row { display:flex; align-items:flex-start; gap:8px; margin-top:6px; }
.score-chip { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; padding:2px 7px; border-radius:3px; white-space:nowrap; flex-shrink:0; }
.chip-leaked { background:#fef2f2; color:#b91c1c; border:1px solid #fca5a5; }
.chip-safe { background:#f0fdf4; color:#15803d; border:1px solid #86efac; }
.chip-nodata { background:#f5f5f5; color:#aaa; border:1px solid #ddd; }
.rationale { font-family:'JetBrains Mono',monospace; font-size:10px; color:#999; font-style:italic; line-height:1.5; }

.summary-line { font-family:'JetBrains Mono',monospace; font-size:11px; padding:8px 0 2px 0; border-top:1px solid #eee; margin-top:12px; }

.garak-probe { border:1px solid #ddd; border-radius:6px; padding:12px; margin-bottom:8px; background:#fff; }
.garak-probe.fail { border-left:3px solid #c0392b; }
.garak-probe.pass { border-left:3px solid #27ae60; }
.probe-status { font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; margin-bottom:8px; }
.probe-status.fail { color:#b91c1c; }
.probe-status.pass { color:#15803d; }
.field-label { font-family:'JetBrains Mono',monospace; font-size:9px; color:#aaa; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; font-weight:600; }
.field-value { font-family:'JetBrains Mono',monospace; font-size:12px; color:#444; line-height:1.5; white-space:pre-wrap; word-break:break-word; }

.empty { text-align:center; padding:60px; color:#ccc; font-family:'JetBrains Mono',monospace; font-size:13px; }
</style>
""", unsafe_allow_html=True)


def load_reports(reports_path):
    files = sorted([f for f in os.listdir(reports_path) if f.endswith(".json")], reverse=True)
    reports = []
    for filename in files:
        try:
            with open(reports_path / filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filename"] = filename
                reports.append(data)
        except Exception:
            pass
    return reports


def is_breached(r):
    conv = r.get("conversation")
    if conv:
        return conv.get("achieved", False)
    prompts = r.get("prompts") or []
    return any(not p.get("passed", True) for p in prompts)


def compute_kpis(reports):
    total = len(reports)
    breached = sum(1 for r in reports if is_breached(r))
    total_turns = sum(
        len(r["conversation"].get("turns", []))
        for r in reports if r.get("conversation")
    )
    pyrit_count = sum(1 for r in reports if r.get("framework") == "pyrit")
    garak_count = sum(1 for r in reports if r.get("framework") == "garak")
    return {
        "total": total, "breached": breached,
        "hardened": total - breached,
        "turns": total_turns,
        "pyrit": pyrit_count, "garak": garak_count,
        "rate": round(breached / total * 100) if total else 0
    }


def e(text):
    if not text:
        return ""
    return html.escape(str(text))


def render_kpis(k):
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi blue">
            <div class="label">Total attacks</div>
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
            <div class="label">Turns logged</div>
            <div class="value">{k['turns']}</div>
            <div class="sub">pyrit conversations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_pyrit(report):
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
            <span class="attack-name">{e(report.get('attack_name',''))}</span>
            <span class="attack-meta">{len(turns)} turns · {leaked_turns} turn-leaked · {ts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View conversation trace", expanded=False):
        objective = conv.get("objective", "")
        if objective:
            st.markdown(f"""
            <div class="objective-box">
                <div class="obj-label">Objective</div>
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
                chip = '<span class="score-chip chip-leaked">⚠ TURN LEAKED</span>'
            else:
                chip = '<span class="score-chip chip-safe">✓ TURN SAFE</span>'

            prompt_html = e(prompt_text) if prompt_text else '<span class="msg-empty">— empty —</span>'
            response_html = e(response_text) if response_text else '<span class="msg-empty">— no response captured —</span>'
            rationale_html = f'<div class="rationale">{e(rationale_text)}</div>' if rationale_text else ''

            st.markdown(f"""
            <div class="turn-block">
                <div class="turn-header">— turn {turn_num} —</div>
                <div class="msg msg-attacker">
                    <div class="msg-label">Attacker</div>
                    {prompt_html}
                </div>
                <div class="msg msg-target">
                    <div class="msg-label">Target</div>
                    {response_html}
                </div>
                <div class="score-row">
                    {chip}
                    {rationale_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

        summary_color = "#c0392b" if achieved else "#27ae60"
        summary_label = "Objective achieved — attack succeeded" if achieved else "Objective not achieved — target held"
        st.markdown(f"""
        <div class="summary-line" style="color:{summary_color}">
            ▸ {summary_label}
        </div>
        """, unsafe_allow_html=True)


def render_garak(report):
    prompts = report.get("prompts") or []
    failed = sum(1 for p in prompts if not p.get("passed", True))
    card_class = "breached" if failed > 0 else "hardened"
    outcome_label = f"{failed} FAILED" if failed > 0 else "ALL PASSED"
    outcome_class = "outcome-breached" if failed > 0 else "outcome-hardened"
    ts = report.get("timestamp", "")[:16].replace("T", " ")

    st.markdown(f"""
    <div class="attack-card {card_class}">
        <div class="attack-header">
            <span class="fw-badge fw-garak">GARAK</span>
            <span class="outcome-badge {outcome_class}">{outcome_label}</span>
            <span class="attack-name">{e(report.get('attack_name',''))}</span>
            <span class="attack-meta">{len(prompts)} probes · {ts}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View probes", expanded=False):
        if not prompts:
            st.markdown('<div class="empty">No probes recorded.</div>', unsafe_allow_html=True)
            return

        for idx, p in enumerate(prompts):
            passed = p.get("passed", True)
            row_class = "pass" if passed else "fail"
            status_label = "✓ PASS" if passed else "✗ FAIL"
            score = p.get("score")
            score_str = f" · score {score}" if score is not None else ""
            detector = p.get("detector", "")
            rationale = p.get("rationale", "")

            c1, c2 = st.columns(2)
            with c1:
                detector_html = f'<div class="field-label" style="margin-top:8px">Detector</div><div class="field-value">{e(detector)}</div>' if detector else ""
                st.markdown(f"""
                <div class="garak-probe {row_class}">
                    <div class="probe-status {row_class}">#{idx+1} {status_label}{score_str}</div>
                    <div class="field-label">Prompt</div>
                    <div class="field-value">{e(p.get('prompt',''))}</div>
                    {detector_html}
                </div>
                """, unsafe_allow_html=True)
            with c2:
                rationale_html = f'<div class="field-label" style="margin-top:8px">Rationale</div><div class="field-value" style="font-style:italic;color:#999">{e(rationale)}</div>' if rationale else ""
                st.markdown(f"""
                <div class="garak-probe {row_class}">
                    <div class="probe-status {row_class}">Response</div>
                    <div class="field-value">{e(p.get('response',''))}</div>
                    {rationale_html}
                </div>
                """, unsafe_allow_html=True)


def main():
    reports_path = Path("reports")

    with st.sidebar:

        st.markdown("**Framework**")
        show_pyrit = st.checkbox("PyRIT", value=True)
        show_garak = st.checkbox("Garak", value=True)
        st.markdown("---")
        st.markdown("**Outcome**")
        show_breached = st.checkbox("Breached", value=True)
        show_hardened = st.checkbox("Hardened", value=True)
        st.markdown("---")
        sort_by = st.selectbox("Sort", ["Latest first", "Oldest first", "Name A→Z"])
        search = st.text_input("Search", placeholder="attack name...")


    if not reports_path.exists() or not any(reports_path.glob("*.json")):
        st.markdown('<div class="empty">No reports found in /reports — run your first attack.</div>', unsafe_allow_html=True)
        return

    reports = load_reports(reports_path)
    render_kpis(compute_kpis(reports))

    filtered = reports
    if not show_pyrit:
        filtered = [r for r in filtered if r.get("framework") != "pyrit"]
    if not show_garak:
        filtered = [r for r in filtered if r.get("framework") != "garak"]
    if not show_breached:
        filtered = [r for r in filtered if not is_breached(r)]
    if not show_hardened:
        filtered = [r for r in filtered if is_breached(r)]
    if search:
        filtered = [r for r in filtered if search.lower() in r.get("attack_name", "").lower()]
    if sort_by == "Oldest first":
        filtered = list(reversed(filtered))
    elif sort_by == "Name A→Z":
        filtered = sorted(filtered, key=lambda r: r.get("attack_name", ""))

    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#aaa;margin-bottom:12px">{len(filtered)} attacks</div>', unsafe_allow_html=True)

    for report in filtered:
        fw = report.get("framework", "")
        if fw == "pyrit":
            render_pyrit(report)
        elif fw == "garak":
            render_garak(report)
        else:
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#aaa;padding:10px">Unknown format: {e(report.get("_filename",""))}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()