"""
Surgeon Call Schedule Generator
Main Streamlit app — Modern UI
"""
import streamlit as st

st.set_page_config(
    page_title="Trauma ACS Scheduler",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Font & base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .sidebar-logo {
    font-size: 22px; font-weight: 700; color: #f1f5f9 !important;
    letter-spacing: -0.5px; padding: 8px 0 4px;
}
[data-testid="stSidebar"] .sidebar-sub {
    font-size: 11px; color: #64748b !important;
    text-transform: uppercase; letter-spacing: 1px;
    padding-bottom: 12px;
}
/* Nav radio buttons */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 8px 12px !important;
    border-radius: 8px !important;
    margin: 2px 0 !important;
    transition: background 0.15s;
    font-size: 13px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.08) !important;
}

/* ── Page header ── */
.page-header {
    padding: 24px 0 8px;
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 24px;
}
.page-header h1 {
    font-size: 26px; font-weight: 700; color: #0f172a;
    letter-spacing: -0.5px; margin: 0;
}
.page-header p { color: #64748b; font-size: 14px; margin: 4px 0 0; }

/* ── Cards ── */
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card-title {
    font-size: 13px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.card-value {
    font-size: 32px; font-weight: 700; color: #0f172a; line-height: 1;
}
.card-sub { font-size: 12px; color: #94a3b8; margin-top: 4px; }

/* ── Stat row ── */
.stat-row { display: flex; gap: 16px; margin-bottom: 24px; }
.stat-item {
    flex: 1; background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 16px 20px;
}

/* ── Section divider ── */
.section-divider {
    border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;
}

/* ── Buttons ── */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 24px !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.35) !important;
    transition: opacity 0.15s !important;
}
[data-testid="stButton"] button[kind="primary"]:hover { opacity: 0.9 !important; }
[data-testid="stButton"] button[kind="secondary"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* ── Inputs ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    font-size: 13px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Step badge ── */
.step-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    background: #3b82f6; color: #fff;
    font-size: 13px; font-weight: 700; margin-right: 10px;
}
.step-row { display: flex; align-items: center; margin-bottom: 12px; font-size: 14px; color: #334155; }

/* ── Tag badge ── */
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 600;
}
.badge-blue  { background: #dbeafe; color: #1d4ed8; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-gray  { background: #f1f5f9; color: #475569; }

/* ── Download buttons ── */
[data-testid="stDownloadButton"] button {
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    width: 100% !important;
}

/* ── Alert boxes ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #6366f1 !important; }
</style>
""", unsafe_allow_html=True)

# ── Seed data ────────────────────────────────────────────────────────────────
from scheduler.data_store import load_surgeons
from scheduler.seed_data import seed
if not load_surgeons():
    seed()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">Trauma ACS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Call Scheduler</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "",
        [
            "🏠  Home",
            "👤  Surgeons",
            "📅  PTO Requests",
            "⚡  Generate Schedule",
            "📋  View Schedule",
            "🗓️  Calendar View",
        ],
        label_visibility="collapsed",
    )


def page_header(title, subtitle=""):
    st.markdown(
        f'<div class="page-header"><h1>{title}</h1>'
        + (f'<p>{subtitle}</p>' if subtitle else "")
        + '</div>',
        unsafe_allow_html=True,
    )


def stat_card(label, value, sub=""):
    return (
        f'<div class="stat-item">'
        f'<div class="card-title">{label}</div>'
        f'<div class="card-value">{value}</div>'
        + (f'<div class="card-sub">{sub}</div>' if sub else "")
        + '</div>'
    )


# ── Home ─────────────────────────────────────────────────────────────────────
if page == "🏠  Home":
    page_header("Trauma ACS Call Scheduler", "Auto-generate fair call schedules for your surgical team.")

    surgeons = load_surgeons()
    trauma_n = len([s for s in surgeons if s.can_do_trauma])
    icu_n    = len([s for s in surgeons if not s.can_do_trauma])

    st.markdown(
        '<div class="stat-row">'
        + stat_card("Trauma Surgeons", trauma_n, "in call pool")
        + stat_card("ICU-Only Staff",  icu_n,    "not in trauma pool")
        + stat_card("Shift Cycle",     "10 wks", "standard block")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### How it works")
    steps = [
        ("Review surgeon profiles", "FTE, roles, night limits"),
        ("Enter PTO / time-off",    "Blocked from block assignment"),
        ("Generate schedule",       "Up to 6 months, auto-balanced"),
        ("Review & export",         "Table view, calendar, or PDF"),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(
            f'<div class="step-row">'
            f'<span class="step-badge">{i}</span>'
            f'<span><b>{title}</b> — {desc}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Surgeons ─────────────────────────────────────────────────────────────────
elif page == "👤  Surgeons":
    import pandas as pd
    from scheduler.data_store import save_surgeons

    page_header("Surgeon Profiles", "Review FTE, roles, and per-10-week shift targets.")

    surgeons = load_surgeons()
    df = pd.DataFrame([{
        "Name": s.name,
        "FTE": s.fte,
        "Trauma": "✓" if s.can_do_trauma else "—",
        "ICU":    "✓" if s.can_do_icu    else "—",
        "Shift Adj": s.shift_adjust,
        "TrEGS/10wk": s.target_tregs_day,
        "ICU/10wk":   s.target_icu_day,
        "Night MTWT": s.target_night_mth,
        "Night FSS":  s.target_night_fss,

        "Notes": s.notes,
    } for s in surgeons])
    st.dataframe(
        df.style.format({"FTE": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
        height=(len(surgeons) + 1) * 35 + 10,
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### Edit Surgeon")

    names = [s.name for s in surgeons]
    selected_name = st.selectbox("Select surgeon", names, label_visibility="collapsed")
    s = next(x for x in surgeons if x.name == selected_name)

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Role & FTE**")
            fte       = st.number_input("FTE", 0.0, 1.0, s.fte, 0.05)
            can_trauma = st.checkbox("Can do Trauma", s.can_do_trauma)
            can_icu    = st.checkbox("Can do ICU",    s.can_do_icu)
            shift_adj  = st.number_input("Shift Adjustment /4wks", value=s.shift_adjust, step=1)
        with col2:
            st.markdown("**Day Targets / 10 wk**")
            t_tregs = st.number_input("TrEGS Day", value=s.target_tregs_day or 0, step=1)
            t_icu   = st.number_input("ICU Day",   value=s.target_icu_day   or 0, step=1)
        with col3:
            st.markdown("**Night Targets / 10 wk**")
            t_mth      = st.number_input("Night Mon–Thu (4 days)", value=s.target_night_mth or 0, step=1)
            t_fss      = st.number_input("Night Fri–Sun", value=s.target_night_fss or 0, step=1)
            color      = st.color_picker("Color", s.color)
            notes      = st.text_input("Notes", s.notes)

    if st.button("Save Changes", type="primary"):
        s.fte = fte; s.can_do_trauma = can_trauma; s.can_do_icu = can_icu
        s.shift_adjust = shift_adj
        s.target_tregs_day = int(t_tregs); s.target_icu_day = int(t_icu)
        s.target_night_mth = int(t_mth);   s.target_night_fss = int(t_fss)
        s.color = color
        s.notes = notes
        save_surgeons(surgeons)
        st.success(f"Saved {s.name}")

# ── PTO Requests ─────────────────────────────────────────────────────────────
elif page == "📅  PTO Requests":
    import pandas as pd
    from datetime import date, timedelta
    from scheduler.data_store import load_pto, save_pto
    from scheduler.models import PTORequest

    page_header("PTO / Time-Off Requests", "Surgeons with PTO are excluded from block assignment.")

    surgeons = load_surgeons()
    surgeon_names = {s.id: s.name for s in surgeons}
    pto_list = load_pto()

    with st.container():
        st.markdown("### Add PTO")
        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1.5])
        with col1:
            surgeon_options = {s.name: s.id for s in surgeons}
            sel_name = st.selectbox("Surgeon", list(surgeon_options.keys()))
            sel_id   = surgeon_options[sel_name]
        with col2:
            pto_start = st.date_input("From", date.today())
        with col3:
            pto_end = st.date_input("To", date.today())
        with col4:
            reason = st.text_input("Reason")
        if st.button("Add PTO", type="primary"):
            new_entries = []
            d = pto_start
            while d <= pto_end:
                new_entries.append(PTORequest(surgeon_id=sel_id, date=d.isoformat(), reason=reason))
                d += timedelta(days=1)
            pto_list.extend(new_entries)
            save_pto(pto_list)
            st.success(f"Added {len(new_entries)} day(s) for {sel_name}")
            st.rerun()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### Current Requests")

    if pto_list:
        df = pd.DataFrame([{
            "Surgeon": surgeon_names.get(r.surgeon_id, r.surgeon_id),
            "Date": r.date,
            "Reason": r.reason,
        } for r in pto_list]).sort_values(["Surgeon", "Date"])

        col1, col2 = st.columns([2, 5])
        with col1:
            filter_name = st.selectbox("Filter", ["All"] + sorted(surgeon_names.values()))
        if filter_name != "All":
            df = df[df["Surgeon"] == filter_name]

        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("Clear ALL PTO"):
            save_pto([])
            st.success("Cleared")
            st.rerun()
    else:
        st.info("No PTO requests yet.")

# ── Generate Schedule ─────────────────────────────────────────────────────────
elif page == "⚡  Generate Schedule":
    import pandas as pd
    from datetime import date
    from scheduler.engine import ScheduleEngine

    page_header("Generate Schedule", "Set a date range and auto-assign all shifts.")

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        start_date = st.date_input("Start date", date(2026, 5, 25))
    with col2:
        end_date = st.date_input("End date", date(2026, 8, 2))
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if start_date < end_date:
            days  = (end_date - start_date).days + 1
            weeks = days / 7
            st.markdown(
                f'<span class="badge badge-blue">{days} days</span>&nbsp;'
                f'<span class="badge badge-gray">{weeks:.1f} weeks</span>',
                unsafe_allow_html=True,
            )

    if start_date >= end_date:
        st.error("End date must be after start date.")
    else:
        st.markdown("")
        if st.button("Generate Schedule", type="primary"):
            with st.spinner("Building schedule…"):
                engine   = ScheduleEngine(start_date, end_date)
                schedule = engine.generate()
            st.success(f"Generated {len(schedule)} days of schedule!")
            st.balloons()

            # Possible schedule patterns given current PTO
            avail = engine.availability_log
            if avail:
                from math import prod
                total_patterns = prod(a["week_combos"] for a in avail)
                bottleneck     = min(avail, key=lambda a: a["week_combos"])
                if total_patterns == 0:
                    pattern_label = "0 — impossible!"
                    delta_color   = "inverse"
                elif total_patterns == 1:
                    pattern_label = "1 — no flexibility"
                    delta_color   = "inverse"
                else:
                    pattern_label = f"{total_patterns:,}"
                    delta_color   = "normal"

                c1, c2 = st.columns(2)
                c1.metric(
                    "Possible Schedule Patterns",
                    pattern_label,
                    help="Total number of valid surgeon assignment combinations across all weeks, given current PTO",
                )
                c2.metric(
                    "Most Constrained Week",
                    bottleneck["week"],
                    delta=f"{bottleneck['week_combos']} pattern{'s' if bottleneck['week_combos'] != 1 else ''}",
                    help="The week with fewest possible combinations",
                )

            surgeons      = load_surgeons()
            monthly_budget = 14.0
            months         = sorted({d.date[:7] for d in schedule})

            # PTO counts excluding weekends and US holidays
            import holidays as _holidays
            from datetime import date as _date
            from scheduler.data_store import load_pto
            us_holidays = _holidays.US(years=range(start_date.year, end_date.year + 1))
            pto_list = load_pto()
            def _workday_pto_count(surgeon_id):
                count = 0
                for p in pto_list:
                    if p.surgeon_id != surgeon_id:
                        continue
                    d = _date.fromisoformat(p.date)
                    if d.weekday() < 5 and d not in us_holidays:
                        count += 1
                return count

            # Total credits in period per surgeon (TrEGS block=7, ICU block=7, Night=1)
            def _total_shifts(surgeon_id):
                return int(round(sum(engine.monthly_credits.get(surgeon_id, {}).values())))

            summary_data = []
            for s in surgeons:
                mc          = engine.monthly_credits.get(s.id, {})
                mtwt_blocks = engine.mtwt_block_counts.get(s.id, 0)
                fss_blocks  = engine.fss_block_counts.get(s.id, 0)
                night_count = mtwt_blocks * 4 + fss_blocks * 3   # total night credits

                # Achievable target = sum of role targets converted to credits
                # TrEGS/ICU: 1 credit per day, Night: MTWT=4 credits, FSS=3 credits
                role_target_10wk = (
                    (s.target_tregs_day  or 0) +
                    (s.target_icu_day    or 0) +
                    (s.target_night_mth  or 0) * 4 +
                    (s.target_night_fss  or 0) * 3 +
                    s.shift_adjust
                )
                # Scale to actual period length.
                # Use raw float (no intermediate rounding) so low-FTE surgeons like
                # Takanishi get accurate targets: 0.4×14×2.5 = 14.0 (not 15 after rounding).
                actual_weeks      = ((end_date - start_date).days + 1) / 7.0
                target_4wks_raw   = s.fte * 14 + s.shift_adjust          # float, e.g. 5.6
                target_10wks_raw  = target_4wks_raw * 2.5                 # float, e.g. 14.0
                target_period     = int(round(target_10wks_raw * actual_weeks / 10.0))
                # Display columns: round for readability
                target_4wks       = round(target_4wks_raw)
                target_10wks      = round(target_10wks_raw)

                row = {
                    "Surgeon":     s.name,
                    "FTE":         s.fte,
                    "Target/4wks": target_4wks,
                    "Target/10wks": target_10wks,
                }
                for m in months:
                    row[m[5:]] = round(mc.get(m, 0))
                tregs_credits = engine.block_week_counts.get(s.id, 0) * 7
                icu_credits   = engine.icu_week_counts_result.get(s.id, 0) * 7
                total_cred    = _total_shifts(s.id)
                row["TrEGS"]          = tregs_credits
                row["ICU"]            = icu_credits
                row["MTWT"]           = mtwt_blocks
                row["FSS"]            = fss_blocks
                row["Tr Nights"]      = night_count
                row["Total"]          = total_cred
                row["Diff"]           = total_cred - target_period
                row["PTO"]            = _workday_pto_count(s.id)
                summary_data.append(row)

            st.markdown("### Shift Credit Summary")
            st.caption("Block week = 7 credits · Night = 1 credit")
            df_summary = pd.DataFrame(summary_data)

            # Totals row — sum numeric columns, label text columns
            totals = {}
            for col in df_summary.columns:
                if col == "Surgeon":
                    totals[col] = "TOTAL"
                elif col == "FTE":
                    totals[col] = round(df_summary[col].sum(), 2)
                else:
                    try:
                        totals[col] = df_summary[col].sum()
                    except TypeError:
                        totals[col] = ""
            df_with_total = pd.concat(
                [df_summary, pd.DataFrame([totals])], ignore_index=True
            )

            def diff_bg(val):
                try:
                    v = int(val)
                    if abs(v) <= 2:  return "#dcfce7", "#166534"
                    elif abs(v) <= 5: return "#fef9c3", "#854d0e"
                    else:             return "#fee2e2", "#991b1b"
                except Exception:
                    return "", ""

            # Render as HTML table for precise column width control
            cols = list(df_with_total.columns)
            th_style = (
                "background:#334155;color:#f1f5f9;font-size:11px;font-weight:700;"
                "padding:5px 6px;text-align:center;white-space:nowrap;"
                "border-bottom:2px solid #94a3b8;border-right:1px solid #475569;"
            )
            td_base = (
                "font-size:11px;padding:4px 6px;text-align:center;color:#1e293b;"
                "border-bottom:1px solid #e2e8f0;border-right:1px solid #e2e8f0;"
            )

            col_widths = {"Surgeon": 68, "FTE": 38, "Target/4wks": 52,
                          "Target/10wks": 54, "Diff": 38, "PTO": 36,
                          "TrEGS": 44, "ICU": 36, "MTWT": 40, "FSS": 36,
                          "Tr Nights": 50, "Total": 40}

            html = ['<div style="overflow-x:auto;border-radius:8px;border:1px solid #cbd5e1;">'
                    '<table style="border-collapse:collapse;width:100%;font-family:sans-serif;">']
            html.append("<thead><tr>")
            for c in cols:
                w = col_widths.get(c, 38)
                html.append(f'<th style="{th_style}min-width:{w}px;max-width:{w}px;">{c}</th>')
            html.append("</tr></thead><tbody>")

            for i, row_data in df_with_total.iterrows():
                is_total = (i == len(df_with_total) - 1)
                row_bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
                if is_total:
                    row_bg = "#1e293b"
                html.append(f'<tr style="background:{row_bg};">')
                for c in cols:
                    val = row_data[c]
                    w   = col_widths.get(c, 38)
                    cell_extra = ""
                    txt_color  = "#1e293b"
                    if is_total:
                        txt_color  = "#f1f5f9"
                        cell_extra = "font-weight:700;"
                    elif c == "Diff":
                        bg, fg = diff_bg(val)
                        if bg:
                            cell_extra = f"background:{bg};font-weight:600;"
                            txt_color  = fg
                    if c == "FTE":
                        disp = f"{val:.2f}" if isinstance(val, float) else val
                    else:
                        disp = "" if (val == "" or (isinstance(val, float) and pd.isna(val))) else val
                    html.append(
                        f'<td style="{td_base}{cell_extra}color:{txt_color};'
                        f'min-width:{w}px;max-width:{w}px;">{disp}</td>'
                    )
                html.append("</tr>")
            html.append("</tbody></table></div>")

            st.markdown("\n".join(html), unsafe_allow_html=True)

# ── View Schedule ─────────────────────────────────────────────────────────────
elif page == "📋  View Schedule":
    import pandas as pd
    from datetime import date
    from scheduler.data_store import load_schedule

    page_header("View Schedule", "Browse by month, filter by surgeon, and export.")

    schedule = load_schedule()
    if not schedule:
        st.warning("No schedule yet — go to ⚡ Generate Schedule first.")
    else:
        surgeons      = load_surgeons()
        surgeon_names = {s.id: s.name for s in surgeons}

        dates        = [date.fromisoformat(d.date) for d in schedule]
        months       = sorted(set((d.year, d.month) for d in dates))
        month_labels = [f"{y}-{m:02d}" for y, m in months]

        col1, col2 = st.columns([2, 3])
        with col1:
            sel_month = st.selectbox("Month", month_labels)
        with col2:
            all_names      = ["All"] + sorted(s.name for s in surgeons)
            filter_surgeon = st.selectbox("Filter by surgeon", all_names)

        sel_year, sel_month_num = map(int, sel_month.split("-"))
        month_schedule = [
            d for d in schedule
            if date.fromisoformat(d.date).year == sel_year
            and date.fromisoformat(d.date).month == sel_month_num
        ]

        def name(sid):
            if not sid or sid == "TBD": return sid or ""
            return surgeon_names.get(sid, sid)

        rows = []
        for ds in month_schedule:
            d = date.fromisoformat(ds.date)
            rows.append({
                "Date": ds.date, "Day": d.strftime("%a"),
                "TrEGS Day":    name(ds.tregs_day),
                "Office":       name(ds.tregs_day_office),
                "ICU Day":      name(ds.icu_day),
                "Tr/EGS/SICU N": name(ds.tr_egs_sicu_night),
                "Tr D b/u":     name(ds.tr_day_backup),
                "Tr N b/u":     name(ds.tr_night_backup),
                "Notes":        ds.notes,
            })

        df = pd.DataFrame(rows)
        if filter_surgeon != "All":
            mask = (
                (df["TrEGS Day"]    == filter_surgeon) |
                (df["ICU Day"]      == filter_surgeon) |
                (df["Tr/EGS/SICU N"] == filter_surgeon) |
                (df["Tr D b/u"]     == filter_surgeon) |
                (df["Tr N b/u"]     == filter_surgeon)
            )
            df = df[mask]

        # Color-coded HTML table
        color_map = {s.name: s.color for s in surgeons}
        def colored_name(n):
            if not n: return ""
            c = color_map.get(n, "#94a3b8")
            return (f'<span style="background:{c};color:#fff;border-radius:4px;'
                    f'padding:1px 7px;font-size:12px;white-space:nowrap;">{n}</span>')

        shift_cols = ["TrEGS Day","Office","ICU Day","Tr/EGS/SICU N","Tr D b/u","Tr N b/u"]
        df_html = df.copy()
        for col in shift_cols:
            df_html[col] = df_html[col].apply(colored_name)

        html_table = df_html.to_html(escape=False, index=False)
        html_table = (
            '<style>table{width:100%;border-collapse:collapse;font-size:13px}'
            'th{background:#1e293b;color:#94a3b8;padding:6px 8px;text-align:left}'
            'td{padding:5px 8px;border-bottom:1px solid #1e293b;vertical-align:middle}'
            'tr:nth-child(even){background:#0f172a}tr:nth-child(odd){background:#1e293b22}'
            '</style>' + html_table
        )
        st.markdown(html_table, unsafe_allow_html=True)

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("### Export")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "⬇ CSV", df.to_csv(index=False),
                f"schedule_{sel_month}.csv", "text/csv",
            )
        with col2:
            import io
            buf = io.BytesIO()
            df.to_excel(buf, index=False)
            st.download_button(
                "⬇ Excel", buf.getvalue(),
                f"schedule_{sel_month}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col3:
            from scheduler.pdf_export import generate_pdf
            month_name  = date(sel_year, sel_month_num, 1).strftime("%B %Y")
            sched_start = min(date.fromisoformat(d.date) for d in schedule)
            pdf_bytes   = generate_pdf(
                month_schedule, {s.id: s.name for s in load_surgeons()},
                month_name, sched_start,
            )
            st.download_button(
                "⬇ PDF", pdf_bytes,
                f"schedule_{sel_month}.pdf", "application/pdf",
            )

# ── Calendar View ─────────────────────────────────────────────────────────────
elif page == "🗓️  Calendar View":
    import calendar
    from datetime import date
    from scheduler.data_store import load_schedule

    page_header("Calendar View", "Monthly overview with colour-coded shift badges.")

    schedule = load_schedule()
    if not schedule:
        st.warning("No schedule yet — go to ⚡ Generate Schedule first.")
    else:
        surgeons      = load_surgeons()
        surgeon_names = {s.id: s.name for s in surgeons}

        dates        = [date.fromisoformat(d.date) for d in schedule]
        months       = sorted(set((d.year, d.month) for d in dates))
        month_labels = [f"{y}-{m:02d}" for y, m in months]

        col1, _ = st.columns([2, 5])
        with col1:
            sel_month = st.selectbox("Month", month_labels, key="cal_month")
        sel_year, sel_month_num = map(int, sel_month.split("-"))

        color_map = {s.name: s.color for s in surgeons}
        sched_map    = {d.date: d for d in schedule}

        def cell(ds):
            s = sched_map.get(ds)
            if not s: return ""
            def tag(sid, label, opacity=""):
                if not sid or sid == "TBD": return ""
                n = surgeon_names.get(sid, sid)
                c = color_map.get(n, "#94a3b8")
                return (
                    f'<div style="background:{c}{opacity};color:#fff;border-radius:4px;'
                    f'padding:1px 5px;margin:1px 0;font-size:10.5px;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                    f'<span style="opacity:.75;font-size:9px;">{label}</span> {n}</div>'
                )
            return (
                tag(s.tregs_day,         "Day") +
                tag(s.icu_day,           "ICU") +
                tag(s.tr_egs_sicu_night, "Nt",  "cc") +
                tag(s.tr_day_backup,     "Db",  "99") +
                tag(s.tr_night_backup,   "Nb",  "99")
            )

        cal        = calendar.monthcalendar(sel_year, sel_month_num)
        month_name = date(sel_year, sel_month_num, 1).strftime("%B %Y")
        today      = date.today().isoformat()

        html = f"""
        <style>
          .cal {{ width:100%; border-collapse:separate; border-spacing:3px; }}
          .cal th {{
            background:#1e293b; color:#94a3b8;
            text-align:center; padding:8px 4px; font-size:11px;
            font-weight:600; letter-spacing:.6px; text-transform:uppercase;
            border-radius:6px;
          }}
          .cal td {{
            background:#fff; border:1px solid #e2e8f0;
            vertical-align:top; padding:6px; min-height:88px;
            border-radius:8px; width:14.28%;
            box-shadow:0 1px 2px rgba(0,0,0,.04);
            transition:box-shadow .15s;
          }}
          .cal td:hover {{ box-shadow:0 4px 12px rgba(0,0,0,.1); }}
          .cal td.today {{ border:2px solid #6366f1; background:#fafafe; }}
          .cal td.empty {{ background:#f8fafc; border-color:#f1f5f9; box-shadow:none; }}
          .day-num {{
            font-size:13px; font-weight:700; color:#334155;
            margin-bottom:4px; line-height:1;
          }}
          .today .day-num {{ color:#6366f1; }}
        </style>
        <div style="font-size:17px;font-weight:700;color:#0f172a;
             letter-spacing:-.3px;margin-bottom:10px;">{month_name}</div>
        <table class="cal">
          <tr>
            <th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th>
            <th>Fri</th><th>Sat</th><th>Sun</th>
          </tr>
        """

        for week in cal:
            html += "<tr>"
            for day_num in week:
                if day_num == 0:
                    html += '<td class="empty"></td>'
                else:
                    ds       = f"{sel_year}-{sel_month_num:02d}-{day_num:02d}"
                    cls      = "today" if ds == today else ""
                    content  = cell(ds)
                    html += f'<td class="{cls}"><div class="day-num">{day_num}</div>{content}</td>'
            html += "</tr>"
        html += "</table>"

        st.markdown(html, unsafe_allow_html=True)

        # Legend
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">'
            'Day = TrEGS Day &nbsp;·&nbsp; ICU = ICU Day &nbsp;·&nbsp; '
            'Nt = Tr/EGS/SICU Night &nbsp;·&nbsp; Db = Tr Day b/u &nbsp;·&nbsp; Nb = Tr Night b/u'
            '</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(all_surgeons))
        for i, sname in enumerate(all_surgeons):
            c = color_map[sname]
            cols[i].markdown(
                f'<div style="background:{c};color:#fff;border-radius:6px;'
                f'text-align:center;padding:4px 6px;font-size:11px;font-weight:600;">'
                f'{sname}</div>',
                unsafe_allow_html=True,
            )
