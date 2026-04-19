"""
Scheduling engine for the Trauma/ACS call schedule.

Algorithm overview:
1. Build 10-week blocks (pair surgeons for week-long day coverage + assign ICU)
2. Expand blocks into daily TrEGS Day assignments (alternating pattern)
3. Assign nightly shifts (Tr Night, EGS/ICU Night)
4. Assign backups
5. Respect PTO and preferences throughout
"""
import random
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .models import Surgeon, PTORequest, ShiftPreference, DaySchedule, WeekBlock
from .data_store import (
    load_surgeons, load_pto, load_preferences,
    save_schedule, save_week_blocks,
)

# Wednesday = special: QUMG covers GS call
WED = 2  # 0=Mon


def date_range(start: date, end: date):
    """Yield each date from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def week_start(d: date) -> date:
    """Return the Monday of the week containing d (blocks run Mon-Sun)."""
    return d - timedelta(days=d.weekday())  # weekday(): Mon=0, Sun=6


def is_weekend_night(d: date) -> bool:
    """Friday, Saturday, Sunday nights."""
    return d.weekday() in (4, 5, 6)


class ScheduleEngine:
    def __init__(
        self,
        start_date: date,
        end_date: date,
        pto_list: Optional[List[PTORequest]] = None,
        prefs_list: Optional[List[ShiftPreference]] = None,
    ):
        self.start = start_date
        self.end = end_date
        self.surgeons: List[Surgeon] = load_surgeons()
        self.surgeon_map: Dict[str, Surgeon] = {s.id: s for s in self.surgeons}
        self.pto: List[PTORequest] = pto_list or load_pto()
        self.prefs: List[ShiftPreference] = prefs_list or load_preferences()

        # Build PTO set: surgeon_id -> set of date strings
        self.pto_dates: Dict[str, set] = defaultdict(set)
        for r in self.pto:
            self.pto_dates[r.surgeon_id].add(r.date)

        # Shift counters per surgeon (for fairness tracking)
        self.counts: Dict[str, Dict[str, int]] = {
            s.id: {"tregs_day": 0, "icu_day": 0, "tr_night": 0, "tr_night_wknd": 0}
            for s in self.surgeons
        }

        # Period length — scale all 10-week targets proportionally
        total_days = (end_date - start_date).days + 1
        self.period_months: float = total_days / 30.44
        self.period_weeks: float  = total_days / 7.0
        self.period_scale: float  = self.period_weeks / 10.0  # e.g. 26wk → 2.6×

        # Monthly credit tracking: surgeon_id -> 'YYYY-MM' -> credits
        # Credits: block week = 7, ICU week = 7, each night = 1
        # Monthly budget per surgeon = 14 × FTE
        self.monthly_credits: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Result
        self.schedule: Dict[str, DaySchedule] = {}
        self.week_blocks: List[WeekBlock] = []
        self.block_week_counts: Dict[str, int] = {}
        self.icu_week_counts_result: Dict[str, int] = {}
        self.mtwt_block_counts: Dict[str, int] = {}
        self.fss_block_counts:  Dict[str, int] = {}
        # Availability log: list of dicts per week {week, trauma_eligible, icu_eligible}
        self.availability_log: List[Dict] = []

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def is_available(self, surgeon_id: str, d: date) -> bool:
        return d.isoformat() not in self.pto_dates.get(surgeon_id, set())

    def _days_per_month(self, ws: date) -> Dict[str, int]:
        """Return {month_key: days} for each month covered by the Mon-Sun week."""
        counts: Dict[str, int] = defaultdict(int)
        for offset in range(7):
            counts[(ws + timedelta(days=offset)).strftime('%Y-%m')] += 1
        return dict(counts)

    def _primary_month(self, week_mon: date) -> str:
        """Month key ('YYYY-MM') that has the most days in the Mon-Sun week."""
        counts = self._days_per_month(week_mon)
        return max(counts, key=lambda k: counts[k])

    def _monthly_budget(self, surgeon: Surgeon) -> float:
        """Monthly credit cap per calendar month (FTE-based, per 4-week month).
        Floor of 7.0 ensures even low-FTE surgeons can be assigned one block week
        (ICU or TrEGS = 7 credits) without immediately hitting the cap."""
        return max(7.0, 14.0 * surgeon.fte + surgeon.shift_adjust)

    def _achievable_10wk(self, surgeon: Surgeon) -> float:
        """Achievable credits per 10 weeks based on role targets.
        TrEGS/ICU: 1 credit per day. MTWT block=4 credits, FSS block=3 credits."""
        return (
            (surgeon.target_tregs_day or 0) +
            (surgeon.target_icu_day   or 0) +
            (surgeon.target_night_mth or 0) * 4 +
            (surgeon.target_night_fss or 0) * 3 +
            surgeon.shift_adjust
        )

    def _monthly_score(self, surgeon: Surgeon, month_key: str) -> float:
        """How full this month is vs monthly budget. Lower = more room."""
        budget = self._monthly_budget(surgeon)
        if budget == 0:
            return float('inf')
        done = self.monthly_credits[surgeon.id].get(month_key, 0)
        return done / budget

    def _period_target(self, surgeon: Surgeon) -> float:
        """Total credits expected over the full scheduling period.
        Uses raw FTE × 14 (no floor) so low-FTE surgeons like Takanishi
        get accurate targets (e.g. 0.4 × 14 × 2.5 = 14 for 10 weeks)."""
        raw = 14.0 * surgeon.fte + surgeon.shift_adjust
        return max(0.0, raw) * self.period_weeks / 4.0

    def _current_total(self, surgeon: Surgeon) -> float:
        """Total credits assigned so far."""
        return sum(self.monthly_credits[surgeon.id].values())

    def _diff_after(self, surgeon: Surgeon, added_credits: float) -> float:
        """Projected Diff (total - target) if added_credits are assigned."""
        return (self._current_total(surgeon) + added_credits) - self._period_target(surgeon)

    def _total_credit_score(self, surgeon: Surgeon) -> float:
        """Ratio of total credits earned vs period target.
        Lower = further behind = should be preferred."""
        target = self._period_target(surgeon)
        if target == 0:
            return float('inf')
        return self._current_total(surgeon) / target

    def _would_exceed_budget(self, surgeon: Surgeon, days_per_month: Dict[str, int]) -> bool:
        """True if assigning these credits would exceed monthly budget in any month."""
        budget = self._monthly_budget(surgeon)
        for month_key, days in days_per_month.items():
            if self.monthly_credits[surgeon.id].get(month_key, 0) + days > budget:
                return True
        return False

    def trauma_surgeons(self) -> List[Surgeon]:
        return [s for s in self.surgeons if s.can_do_trauma]

    def icu_surgeons(self) -> List[Surgeon]:
        return [s for s in self.surgeons if s.can_do_icu]

    def pick_surgeon(
        self,
        candidates: List[Surgeon],
        d: date,
        shift_key: str,
        target_key: str,
        exclude: Optional[set] = None,
        quota: Optional[Dict[str, int]] = None,
        night_dpm: Optional[Dict[str, int]] = None,
    ) -> Optional[str]:
        """Pick surgeon using quota-based fairness + monthly budget cap."""
        exclude = exclude or set()
        eligible = [
            s for s in candidates
            if self.is_available(s.id, d) and s.id not in exclude
            and (getattr(s, target_key) or 0) > 0
        ]
        if not eligible:
            return None

        month_key = d.strftime('%Y-%m')
        dpm = night_dpm or {month_key: 1}

        def score(s: Surgeon) -> tuple:
            q = (quota or {}).get(s.id, 0)
            if q == 0:
                return (2, 2, float("inf"), float("inf"), 0)
            over_budget   = 1 if self._would_exceed_budget(s, dpm) else 0
            quota_filled  = 1 if self.counts[s.id].get(shift_key, 0) >= q else 0
            progress      = self.counts[s.id].get(shift_key, 0) / q
            monthly_score = self._monthly_score(s, month_key)
            return (over_budget, quota_filled, progress, monthly_score, random.random())

        eligible.sort(key=score)
        return eligible[0].id

    # ------------------------------------------------------------------ #
    # Phase 1: Build weekly blocks
    # ------------------------------------------------------------------ #

    def build_week_blocks(self) -> List[WeekBlock]:
        """
        Assign Block1, Block2, ICU for each week in the period.
        Weeks run Sun→Sat. Each week needs 2 trauma surgeons + 1 ICU surgeon.
        Constraints:
        - Surgeon can't be both block and ICU same week
        - Respect PTO (if surgeon has PTO mid-week, flag but still assign)
        - Distribute fairly by FTE-targets
        """
        blocks = []
        # Collect all week-start Sundays
        week_starts = []
        d = self.start
        # First Monday on or after self.start
        # (blocks run Mon-Sun; any days before first Monday belong to first block)
        if d.weekday() == 0:
            first_mon = d
        else:
            first_mon = d + timedelta(days=(7 - d.weekday()))
        mon = first_mon
        while mon <= self.end:
            week_starts.append(mon)
            mon += timedelta(days=7)

        # Week-level counters
        block_counts    = defaultdict(int)
        icu_week_counts = defaultdict(int)

        n_weeks  = len(week_starts)
        trauma   = self.trauma_surgeons()
        icu_pool = self.icu_surgeons()

        # ── Pre-compute target block-week quotas ──────────────────────────
        # TrEGS: 2 slots per week × n_weeks total slots
        tregs_slots       = n_weeks * 2
        trauma_targeted   = [s for s in trauma if (s.target_tregs_day or 0) > 0]
        total_tregs_t     = sum(s.target_tregs_day for s in trauma_targeted) or 1
        tregs_quota: Dict[str, int] = {}
        for s in trauma_targeted:
            tregs_quota[s.id] = max(1, round(s.target_tregs_day / total_tregs_t * tregs_slots))

        # ICU: 1 slot per week × n_weeks total slots
        icu_slots         = n_weeks
        icu_targeted      = [s for s in icu_pool if (s.target_icu_day or 0) > 0]
        total_icu_t       = sum(s.target_icu_day for s in icu_targeted) or 1
        icu_quota: Dict[str, int] = {}
        for s in icu_targeted:
            icu_quota[s.id] = max(1, round(s.target_icu_day / total_icu_t * icu_slots))
        # ─────────────────────────────────────────────────────────────────

        prev_icu: Optional[str] = None  # ICU surgeon assigned last week (no-consecutive rule)

        for ws in week_starts:
            we = ws + timedelta(days=6)

            # Exact days per month for this week (handles month-spanning weeks)
            days_per_month = self._days_per_month(ws)
            week_month     = self._primary_month(ws)

            # Score: (over_budget, over_diff_cap, quota_filled, role_progress, monthly, random)
            # role_progress = blocks_done / quota  → lower means more quota remaining → preferred
            # over_diff_cap only applies AFTER quota is filled, so quota is always reachable
            block_credits = sum(days_per_month.values())  # typically 7

            def trauma_score(s: Surgeon) -> tuple:
                quota = tregs_quota.get(s.id, 0)
                if quota == 0:
                    return (2, 2, 2, float("inf"), float("inf"), 0)
                over_budget   = 1 if self._would_exceed_budget(s, days_per_month) else 0
                quota_done    = block_counts[s.id]
                quota_filled  = 1 if quota_done >= quota else 0
                over_diff_cap = 0 if quota_done < quota else (1 if self._diff_after(s, block_credits) > -3 else 0)
                role_progress = quota_done / quota   # trauma-specific progress ratio
                monthly_score = self._monthly_score(s, week_month)
                return (over_budget, over_diff_cap, quota_filled, role_progress, monthly_score, random.random())

            trauma_available = [s for s in trauma if self._week_available(s.id, ws, we)]
            trauma_sorted    = sorted(trauma_available, key=trauma_score)

            block1 = trauma_sorted[0].id if len(trauma_sorted) >= 1 else None
            block2 = trauma_sorted[1].id if len(trauma_sorted) >= 2 else None

            def icu_score(s: Surgeon) -> tuple:
                quota = icu_quota.get(s.id, 0)
                if quota == 0:
                    return (2, 2, 2, float("inf"), float("inf"), 0)
                over_budget   = 1 if self._would_exceed_budget(s, days_per_month) else 0
                quota_done    = icu_week_counts[s.id]
                quota_filled  = 1 if quota_done >= quota else 0
                over_diff_cap = 0 if quota_done < quota else (1 if self._diff_after(s, block_credits) > -3 else 0)
                role_progress = quota_done / quota   # ICU-specific progress ratio
                monthly_score = self._monthly_score(s, week_month)
                return (over_budget, over_diff_cap, quota_filled, role_progress, monthly_score, random.random())

            # No consecutive ICU weeks: exclude whoever did ICU last week.
            # If only one candidate remains after exclusion, allow the repeat as a fallback.
            icu_base = [s for s in icu_pool
                        if s.id not in (block1, block2)
                        and self._week_available(s.id, ws, we)
                        and (s.target_icu_day or 0) > 0]
            icu_no_consec = [s for s in icu_base if s.id != prev_icu]
            icu_available     = icu_no_consec if icu_no_consec else icu_base
            icu_pool_filtered = sorted(icu_available, key=icu_score)
            icu = icu_pool_filtered[0].id if icu_pool_filtered else None

            # Credit each surgeon exactly the number of days in each month
            if block1:
                block_counts[block1] += 1
                for m, d in days_per_month.items():
                    self.monthly_credits[block1][m] += d
            if block2:
                block_counts[block2] += 1
                for m, d in days_per_month.items():
                    self.monthly_credits[block2][m] += d
            if icu:
                icu_week_counts[icu] += 1
                for m, d in days_per_month.items():
                    self.monthly_credits[icu][m] += d

            prev_icu = icu  # update for next week's consecutive check

            n_trauma = len(trauma_sorted)
            n_icu    = len(icu_pool_filtered)
            # Combinations for this week: C(n_trauma, 2) * n_icu
            from math import comb
            week_combos = comb(n_trauma, 2) * max(n_icu, 1)
            self.availability_log.append({
                "week": ws.isoformat(),
                "trauma_eligible": n_trauma,
                "icu_eligible": n_icu,
                "week_combos": week_combos,
            })

            blocks.append(
                WeekBlock(
                    week_start=ws.isoformat(),
                    block1_surgeon=block1 or "TBD",
                    block2_surgeon=block2 or "TBD",
                    icu_surgeon=icu or "TBD",
                )
            )

        self.week_blocks = blocks
        self.block_week_counts = dict(block_counts)
        self.icu_week_counts_result = dict(icu_week_counts)
        return blocks

    def _week_available(self, surgeon_id: str, ws: date, we: date) -> bool:
        """True only if surgeon has NO PTO during the entire Mon-Sun block week."""
        return all(self.is_available(surgeon_id, d) for d in date_range(ws, we))

    # ------------------------------------------------------------------ #
    # Phase 2: Expand blocks → daily TrEGS Day + ICU Day
    # ------------------------------------------------------------------ #

    def expand_daily(self):
        """
        For each week block, assign TrEGS Day and ICU Day for each day.
        Pattern: Block1 and Block2 alternate daily.
        Block that starts on Monday alternates each week (week A: block1 starts Mon,
        week B: block2 starts Mon).
        """
        # Build week lookup (each block is Mon-Sun, week_start = Monday)
        week_map: Dict[str, WeekBlock] = {}
        for wb in self.week_blocks:
            mon = date.fromisoformat(wb.week_start)  # always a Monday
            for offset in range(7):  # Mon(+0) through Sun(+6)
                week_map[(mon + timedelta(days=offset)).isoformat()] = wb

        # Days before the first Monday (e.g. schedule starts on Sunday)
        # belong to the first block week
        if self.week_blocks:
            first_wb = self.week_blocks[0]
            first_mon = date.fromisoformat(first_wb.week_start)
            d = self.start
            while d < first_mon:
                week_map[d.isoformat()] = first_wb
                d += timedelta(days=1)

        # Track week index for alternating which block surgeon starts on Monday
        # Even week index: Block1 on Mon/Wed/Fri/Sun, Block2 on Tue/Thu/Sat
        # Odd  week index: Block2 on Mon/Wed/Fri/Sun, Block1 on Tue/Thu/Sat
        week_index: Dict[str, int] = {}
        for i, wb in enumerate(self.week_blocks):
            mon = date.fromisoformat(wb.week_start)
            for offset in range(7):
                week_index[(mon + timedelta(days=offset)).isoformat()] = i
        # Days before first Monday get index 0
        if self.week_blocks:
            first_mon = date.fromisoformat(self.week_blocks[0].week_start)
            d = self.start
            while d < first_mon:
                week_index[d.isoformat()] = 0
                d += timedelta(days=1)

        for d in date_range(self.start, self.end):
            ds = d.isoformat()
            wb = week_map.get(ds)
            if not wb:
                continue

            day_schedule = self.schedule.setdefault(
                ds,
                DaySchedule(date=ds, block1=wb.block1_surgeon, block2=wb.block2_surgeon),
            )
            day_schedule.block1 = wb.block1_surgeon
            day_schedule.block2 = wb.block2_surgeon

            # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
            dow = d.weekday()

            wi = week_index.get(ds, 0)
            # Even week index: Block1 covers Mon/Wed/Fri/Sun (dow%2==0), Block2 covers Tue/Thu/Sat
            # Odd  week index: Block2 covers Mon/Wed/Fri/Sun,             Block1 covers Tue/Thu/Sat
            # (This gives Block1 four days one week, three days the next — balanced over two weeks)
            if wi % 2 == 0:
                tregs_surgeon = wb.block1_surgeon if dow % 2 == 0 else wb.block2_surgeon
            else:
                tregs_surgeon = wb.block2_surgeon if dow % 2 == 0 else wb.block1_surgeon

            # If chosen surgeon has PTO, fall back to the other
            if not self.is_available(tregs_surgeon, d):
                tregs_surgeon = wb.block2_surgeon if tregs_surgeon == wb.block1_surgeon else wb.block1_surgeon

            day_schedule.tregs_day = tregs_surgeon
            day_schedule.icu_day = wb.icu_surgeon

            # Office = Tue(1) and Fri(4): the block surgeon NOT doing TrEGS Day
            if dow in (1, 4):
                off_block = (
                    wb.block2_surgeon if tregs_surgeon == wb.block1_surgeon
                    else wb.block1_surgeon
                )
                if off_block and off_block != "TBD":
                    day_schedule.tregs_day_office = off_block

            # Wednesday note
            if dow == WED:
                day_schedule.notes = "UH Gr Rds, M&M"

    # ------------------------------------------------------------------ #
    # Phase 3: Assign nightly shifts (3-consecutive-day blocks)
    # ------------------------------------------------------------------ #

    def assign_nights(self):
        """
        Assign Trauma Night in consecutive-day blocks.

        Each week is divided into two night blocks:
          - MTWT block : Mon + Tue + Wed + Thu  (4 nights, weekday) → 1 surgeon
          - FSS  block : Fri + Sat + Sun        (3 nights, weekend) → 1 surgeon

        Fairness: quota tracks BLOCKS (not individual nights) so progress ratios
        are comparable across surgeons regardless of block length.
        """
        trauma = self.trauma_surgeons()

        # Collect all Mon-starts for weeks that overlap with our period
        week_mons: List[date] = []
        d = self.start
        mon = d - timedelta(days=d.weekday())
        while mon <= self.end + timedelta(days=6):
            week_mons.append(mon)
            mon += timedelta(days=7)

        n_night_weeks = len(week_mons)

        # Pre-compute night block quotas (in blocks, not nights)
        mth_targeted  = [s for s in trauma if (s.target_night_mth or 0) > 0]
        total_mth_t   = sum(s.target_night_mth for s in mth_targeted) or 1
        mth_quota: Dict[str, int] = {
            s.id: max(1, round(s.target_night_mth / total_mth_t * n_night_weeks))
            for s in mth_targeted
        }
        fss_targeted  = [s for s in trauma if (s.target_night_fss or 0) > 0]
        total_fss_t   = sum(s.target_night_fss for s in fss_targeted) or 1
        fss_quota: Dict[str, int] = {
            s.id: max(1, round(s.target_night_fss / total_fss_t * n_night_weeks))
            for s in fss_targeted
        }

        # Block-level counters (1 per block assignment, NOT per night)
        # Used for fair quota tracking — separate from self.counts which tracks nights
        mtwt_block_counts: Dict[str, int] = defaultdict(int)
        fss_block_counts:  Dict[str, int] = defaultdict(int)

        for week_mon in week_mons:
            # MTWT: Mon(+0), Tue(+1), Wed(+2), Thu(+3)
            # FSS:  Fri(+4), Sat(+5), Sun(+6)
            blocks = [
                ("mtwt", [week_mon + timedelta(days=i) for i in range(4)]),
                ("fss",  [week_mon + timedelta(days=i) for i in range(4, 7)]),
            ]

            # Each surgeon can hold at most ONE night block per calendar week
            assigned_this_week: set = set()

            for block_type, days in blocks:
                # Filter to days within our schedule period
                days_in_range = [d for d in days if self.start <= d <= self.end]
                if not days_in_range:
                    continue

                target_key  = "target_night_fss" if block_type == "fss" else "target_night_mth"
                shift_key   = "tr_night_wknd"    if block_type == "fss" else "tr_night"
                night_quota = fss_quota           if block_type == "fss" else mth_quota
                block_counts = fss_block_counts   if block_type == "fss" else mtwt_block_counts

                # Exclusion set:
                # (a) already have a night block this week
                # (b) have day shift on any night in this block
                # (c) have day shift the NEXT morning (back-to-back prevention)
                exclude: set = set(assigned_this_week)
                for d in days_in_range:
                    ds = d.isoformat()
                    sched = self.schedule.get(ds)
                    if sched:
                        exclude.add(sched.tregs_day)
                        exclude.add(sched.icu_day)
                    next_day = d + timedelta(days=1)
                    next_sched = self.schedule.get(next_day.isoformat())
                    if next_sched:
                        exclude.add(next_sched.tregs_day)
                        exclude.add(next_sched.icu_day)

                # MTWT: exclude surgeon who did FSS block the previous week.
                # FSS ends Sunday; MTWT starts Monday = consecutive nights across weeks.
                if block_type == "mtwt":
                    sunday = days_in_range[0] - timedelta(days=1)   # day before Monday
                    sun_sched = self.schedule.get(sunday.isoformat())
                    if sun_sched and sun_sched.tr_egs_sicu_night:
                        exclude.add(sun_sched.tr_egs_sicu_night)

                # FSS: exclude surgeon who did MTWT this same week.
                # (FSS→next-week-block back-to-back is handled by fix_back_to_back()
                #  which swaps Monday TrEGS if needed — no need to exclude here.)
                next_week_block_ids: set = set()
                if block_type == "fss":
                    thu_sched = self.schedule.get((week_mon + timedelta(days=3)).isoformat())
                    if thu_sched and thu_sched.tr_egs_sicu_night:
                        exclude.add(thu_sched.tr_egs_sicu_night)

                exclude.discard(None)

                # Per-month credit map for this block
                night_days_per_month: Dict[str, int] = defaultdict(int)
                for nd in days_in_range:
                    night_days_per_month[nd.strftime('%Y-%m')] += 1

                def _build_eligible(excl: set) -> List[Surgeon]:
                    return [
                        s for s in trauma
                        if s.id not in excl
                        and (getattr(s, target_key) or 0) > 0
                        and all(self.is_available(s.id, d) for d in days_in_range)
                    ]

                # Consecutive-shift prevention takes priority over quota guarantees.
                # If no eligible surgeon exists under strict exclusions, leave unassigned.
                eligible = _build_eligible(exclude)

                night_credits = len(days_in_range)  # 4 for MTWT, 3 for FSS

                def night_score(s: Surgeon) -> tuple:
                    """
                    Sort key for night block assignment.
                    Priority (ascending = better):
                      0: night quota already filled?         ← quota guarantee (hard-ish)
                      1: night-specific progress ratio       ← distribute evenly within quota
                      2: how full is this month?             ← soft pressure toward Target/4wks
                      3: random tiebreak
                    No hard over_budget exclusion: using monthly_score as a soft signal
                    ensures surgeons with less-full months are preferred, while still
                    allowing quota to be reached even in high-credit months.
                    """
                    quota = night_quota.get(s.id, 0)
                    if quota == 0:
                        return (2, float("inf"), float("inf"), 0)
                    blocks_done    = block_counts[s.id]
                    quota_filled   = 1 if blocks_done >= quota else 0
                    night_progress = blocks_done / quota
                    month_key      = days_in_range[0].strftime('%Y-%m')
                    monthly_sc     = self._monthly_score(s, month_key)
                    return (quota_filled, night_progress, monthly_sc, random.random())

                if eligible:
                    eligible.sort(key=night_score)
                    surgeon_id = eligible[0].id
                else:
                    surgeon_id = None

                # Assign to each day in the block
                for d in days_in_range:
                    ds = d.isoformat()
                    day_sched = self.schedule.setdefault(ds, DaySchedule(date=ds))
                    if surgeon_id:
                        day_sched.tr_egs_sicu_night = surgeon_id

                if surgeon_id:
                    block_counts[surgeon_id] += 1          # track BLOCKS for fairness
                    assigned_this_week.add(surgeon_id)
                    self.counts[surgeon_id][shift_key] += len(days_in_range)  # track nights
                    for nd in days_in_range:
                        self.monthly_credits[surgeon_id][nd.strftime('%Y-%m')] += 1

        # ── FSS equalization pass ─────────────────────────────────────────
        # After normal assignment, ensure every FSS-targeted surgeon gets exactly 1 block.
        # Surgeons like Inouye (many ICU weeks) can be excluded from too many FSS weeks
        # during normal scheduling. Here we steal a week from an over-assigned surgeon.
        for s in fss_targeted:
            if fss_block_counts[s.id] >= 1:
                continue  # already has their block

            # Find a week where s is eligible AND the current FSS assignee has > 1 block
            for week_mon in week_mons:
                fss_days = [week_mon + timedelta(days=i) for i in range(4, 7)]
                fss_in_range = [d for d in fss_days if self.start <= d <= self.end]
                if not fss_in_range:
                    continue

                # Hard eligibility: available all FSS days
                if not all(self.is_available(s.id, d) for d in fss_in_range):
                    continue

                # Hard eligibility: not doing day shift on FSS days
                day_conflict = any(
                    (self.schedule.get(d.isoformat()) or DaySchedule(date=d.isoformat())).tregs_day == s.id
                    or (self.schedule.get(d.isoformat()) or DaySchedule(date=d.isoformat())).icu_day == s.id
                    for d in fss_in_range
                )
                if day_conflict:
                    continue

                # Hard eligibility: not doing ICU/TrEGS next Monday morning
                next_mon_sched = self.schedule.get((week_mon + timedelta(days=7)).isoformat())
                if next_mon_sched and (
                    next_mon_sched.tregs_day == s.id or next_mon_sched.icu_day == s.id
                ):
                    continue

                # Find who is currently assigned to this FSS block
                first_sched = self.schedule.get(fss_in_range[0].isoformat())
                current_id = first_sched.tr_egs_sicu_night if first_sched else None

                if current_id and fss_block_counts.get(current_id, 0) > 1:
                    # Swap: give this block to the under-assigned surgeon
                    for d in fss_in_range:
                        day_s = self.schedule.get(d.isoformat())
                        if day_s and day_s.tr_egs_sicu_night == current_id:
                            day_s.tr_egs_sicu_night = s.id
                    fss_block_counts[current_id] -= 1
                    fss_block_counts[s.id] += 1
                    for d in fss_in_range:
                        mk = d.strftime('%Y-%m')
                        self.monthly_credits[current_id][mk] -= 1
                        self.monthly_credits[s.id][mk] += 1
                    break  # done for this surgeon

        # Expose block counts for Shift Credit Summary
        self.mtwt_block_counts = dict(mtwt_block_counts)
        self.fss_block_counts  = dict(fss_block_counts)

    # ------------------------------------------------------------------ #
    # Phase 3b: Fix back-to-back (night → next morning day shift)
    # ------------------------------------------------------------------ #

    def fix_back_to_back(self):
        """
        After nights are assigned, scan every day D:
        If the TrEGS Day surgeon did Tr Night on D-1, swap to the other block surgeon.

        Critically: when day D is swapped from A→B, also swap day D+1 from B→A
        (within the same week block) to preserve the Mon/Tue alternating pattern.
        If both block surgeons have conflicts, mark as TBD and log a warning.
        """
        warnings = []
        for d in date_range(self.start, self.end):
            ds = d.isoformat()
            sched = self.schedule.get(ds)
            if not sched or not sched.tregs_day:
                continue

            prev_day = d - timedelta(days=1)
            prev_sched = self.schedule.get(prev_day.isoformat())
            if not prev_sched or not prev_sched.tr_egs_sicu_night:
                continue

            # Conflict: TrEGS Day surgeon was on night the night before
            if sched.tregs_day != prev_sched.tr_egs_sicu_night:
                continue

            original = sched.tregs_day
            other = sched.block2 if original == sched.block1 else sched.block1

            if not other or other == "TBD":
                continue

            other_also_conflict = (prev_sched.tr_egs_sicu_night == other)

            if not other_also_conflict and self.is_available(other, d):
                # Swap day D: A → B
                sched.tregs_day = other

                # Preserve alternation: swap day D+1 from B → A if same week block
                # Only within the same Mon-Sun week (don't cross week boundary at Sun→Mon)
                next_day = d + timedelta(days=1)
                next_ds = next_day.isoformat()
                next_sched = self.schedule.get(next_ds)
                same_week = (d.weekday() != 6)  # Sunday(6) is last day of block; Mon starts new block
                if (
                    same_week
                    and next_sched
                    and next_sched.block1 == sched.block1
                    and next_sched.block2 == sched.block2  # verify both block slots match
                    and next_sched.tregs_day == other
                    and self.is_available(original, next_day)
                    and (not sched.tr_egs_sicu_night or sched.tr_egs_sicu_night != original)
                ):
                    next_sched.tregs_day = original
            else:
                warnings.append(
                    f"  ⚠️  {ds}: both block surgeons have back-to-back conflict "
                    f"({sched.block1} / {sched.block2})"
                )
                sched.tregs_day = "TBD"

        if warnings:
            print("Back-to-back warnings:")
            for w in warnings:
                print(w)

    # ------------------------------------------------------------------ #
    # Phase 4: Assign backups
    # ------------------------------------------------------------------ #

    def assign_backups(self):
        """Assign Trauma Day backup and Trauma Night backup."""
        trauma = self.trauma_surgeons()

        for d in date_range(self.start, self.end):
            ds = d.isoformat()
            day_sched = self.schedule.get(ds)
            if not day_sched:
                continue

            already_assigned = {
                day_sched.tregs_day,
                day_sched.icu_day,
                day_sched.tr_egs_sicu_night,
            }

            # Day backup = the block surgeon from TODAY who is NOT doing TrEGS Day
            if day_sched.block1 and day_sched.block2:
                if day_sched.tregs_day == day_sched.block1:
                    day_bu = day_sched.block2
                elif day_sched.tregs_day == day_sched.block2:
                    day_bu = day_sched.block1
                else:
                    day_bu = None

                if day_bu and day_bu != "TBD":
                    day_sched.tr_day_backup = day_bu
                    already_assigned.add(day_bu)
                else:
                    eligible = [s for s in trauma if self.is_available(s.id, d) and s.id not in already_assigned]
                    if eligible:
                        day_sched.tr_day_backup = eligible[0].id
                        already_assigned.add(eligible[0].id)
            else:
                eligible = [s for s in trauma if self.is_available(s.id, d) and s.id not in already_assigned]
                if eligible:
                    day_sched.tr_day_backup = eligible[0].id
                    already_assigned.add(eligible[0].id)

            # Night backup = the block surgeon from TOMORROW who is NOT doing TrEGS Day tomorrow
            # (the "off" block surgeon the next day)
            next_day = d + timedelta(days=1)
            next_sched = self.schedule.get(next_day.isoformat())
            if next_sched and next_sched.block1 and next_sched.block2:
                # One of block1/block2 is on TrEGS Day tomorrow; the other is the backup
                if next_sched.tregs_day == next_sched.block1:
                    night_bu = next_sched.block2
                elif next_sched.tregs_day == next_sched.block2:
                    night_bu = next_sched.block1
                else:
                    night_bu = None  # unusual case (e.g. TBD)

                if night_bu and night_bu != "TBD":
                    day_sched.tr_night_backup = night_bu
                else:
                    # Fallback: pick anyone not already assigned
                    eligible2 = [
                        s for s in trauma
                        if self.is_available(s.id, d) and s.id not in already_assigned
                    ]
                    if eligible2:
                        day_sched.tr_night_backup = eligible2[0].id
            else:
                # No next-day block info (e.g. last day of schedule)
                eligible2 = [
                    s for s in trauma
                    if self.is_available(s.id, d) and s.id not in already_assigned
                ]
                if eligible2:
                    day_sched.tr_night_backup = eligible2[0].id

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    def generate(self) -> List[DaySchedule]:
        print("Building week blocks...")
        self.build_week_blocks()

        print("Expanding daily assignments...")
        self.expand_daily()

        print("Assigning nights...")
        self.assign_nights()

        print("Fixing back-to-back conflicts...")
        self.fix_back_to_back()

        print("Assigning backups...")
        self.assign_backups()

        schedule_list = [self.schedule[d.isoformat()] for d in date_range(self.start, self.end) if d.isoformat() in self.schedule]
        schedule_list.sort(key=lambda x: x.date)

        save_schedule(schedule_list)
        save_week_blocks(self.week_blocks)

        print(f"Done. Generated {len(schedule_list)} days.")
        return schedule_list
