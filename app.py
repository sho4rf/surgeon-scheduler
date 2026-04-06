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
        "Night MTh":  s.target_night_mth,
        "Night FSS":  s.target_night_fss,
        "Max Consec Nights": s.max_consecutive_nights,
        "Notes": s.notes,
    } for s in surgeons])
    st.dataframe(
        df.style.format({"FTE": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
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
            shift_adj  = st.number_input("Shift Adjustment", value=s.shift_adjust, step=1)
        with col2:
            st.markdown("**Day Targets / 10 wk**")
            t_tregs = st.number_input("TrEGS Day", value=s.target_tregs_day or 0, step=1)
            t_icu   = st.number_input("ICU Day",   value=s.target_icu_day   or 0, step=1)
        with col3:
            st.markdown("**Night Targets / 10 wk**")
            t_mth      = st.number_input("Night Mon–Thu", value=s.target_night_mth or 0, step=1)
            t_fss      = st.number_input("Night Fri–Sun", value=s.target_night_fss or 0, step=1)
            max_nights = st.number_input("Max Consecutive Nights", 1, 7, s.max_consecutive_nights, 1)
            notes      = st.text_input("Notes", s.notes)

    if st.button("Save Changes", type="primary"):
        s.fte = fte; s.can_do_trauma = can_trauma; s.can_do_icu = can_icu
        s.shift_adjust = shift_adj
        s.target_tregs_day = int(t_tregs); s.target_icu_day = int(t_icu)
        s.target_night_mth = int(t_mth);   s.target_night_fss = int(t_fss)
        s.max_consecutive_nights = int(max_nights); s.notes = notes
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

            surgeons      = load_surgeons()
            monthly_budget = 14.0
            months         = sorted({d.date[:7] for d in schedule})

            summary_data = []
            for s in surgeons:
                mc             = engine.monthly_credits.get(s.id, {})
                monthly_totals = [round(mc.get(m, 0)) for m in months]
                avg            = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0
                target         = round(monthly_budget * s.fte, 1)
                night_count    = sum(1 for d in schedule if d.tr_egs_sicu_night == s.id)
                row = {"Surgeon": s.name, "FTE": round(s.fte, 1), "Target/mo": int(round(target)), "Avg/mo": int(round(avg)), "Diff": int(round(avg - target))}
                for m in months:
                    row[m[5:]] = round(mc.get(m, 0))
                row["Tr Nights"] = night_count
                summary_data.append(row)

            st.markdown("### Shift Credit Summary")
            st.caption("Block week = 7 credits · Night = 1 credit")
            df_summary = pd.DataFrame(summary_data)

            def colour_diff(val):
                if abs(val) <= 2:   return "background-color:#dcfce7;color:#166534"
                elif abs(val) <= 4: return "background-color:#fef9c3;color:#854d0e"
                else:               return "background-color:#fee2e2;color:#991b1b"

            st.dataframe(
                df_summary.style.applymap(colour_diff, subset=["Diff"]),
                use_container_width=True, hide_index=True,
            )

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

        st.dataframe(df, use_container_width=True, height=560, hide_index=True)

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

        COLORS = [
            "#3b82f6","#f59e0b","#ef4444","#10b981","#8b5cf6",
            "#f97316","#06b6d4","#ec4899","#84cc16","#6366f1","#14b8a6",
        ]
        all_surgeons = [s.name for s in surgeons]
        color_map    = {n: COLORS[i % len(COLORS)] for i, n in enumerate(all_surgeons)}
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
