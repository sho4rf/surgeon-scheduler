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
        period_weeks = total_days / 7.0
        self.period_scale: float = period_weeks / 10.0  # e.g. 26wk → 2.6×

        # Monthly credit tracking: surgeon_id -> 'YYYY-MM' -> credits
        # Credits: block week = 7, ICU week = 7, each night = 1
        # Monthly budget per surgeon = 14 × FTE
        self.monthly_credits: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Result
        self.schedule: Dict[str, DaySchedule] = {}
        self.week_blocks: List[WeekBlock] = []
        self.block_week_counts: Dict[str, int] = {}
        self.icu_week_counts_result: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def is_available(self, surgeon_id: str, d: date) -> bool:
        return d.isoformat() not in self.pto_dates.get(surgeon_id, set())

    def _primary_month(self, week_mon: date) -> str:
        """Month key ('YYYY-MM') that has the most days in the Mon-Sun week."""
        counts: Dict[str, int] = defaultdict(int)
        for offset in range(7):
            counts[(week_mon + timedelta(days=offset)).strftime('%Y-%m')] += 1
        return max(counts, key=lambda k: counts[k])

    def _monthly_score(self, surgeon: Surgeon, month_key: str) -> float:
        """How 'full' this surgeon's month is relative to their 14×FTE budget.
        Lower = more room = should be preferred."""
        budget = 14.0 * surgeon.fte
        if budget == 0:
            return float('inf')
        done = self.monthly_credits[surgeon.id].get(month_key, 0)
        return done / budget

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
    ) -> Optional[str]:
        """
        Pick the surgeon who is:
        - available (no PTO)
        - not in exclude set
        - furthest below their target count (greedy fairness)
        """
        exclude = exclude or set()
        eligible = [
            s for s in candidates
            if self.is_available(s.id, d) and s.id not in exclude
        ]
        if not eligible:
            return None

        def score(s: Surgeon) -> tuple:
            target = (getattr(s, target_key) or 0) * self.period_scale
            if target == 0:
                return (float("inf"), float("inf"))
            done = self.counts[s.id].get(shift_key, 0)
            global_score = done / target
            month_key = d.strftime('%Y-%m')
            monthly_score = self._monthly_score(s, month_key)
            return (global_score, monthly_score)

        eligible = [s for s in eligible if (getattr(s, target_key) or 0) > 0]
        if not eligible:
            return None

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

        # Week-level counters for blocks (each block week = 7 credited shifts per surgeon)
        block_counts = defaultdict(int)    # surgeon_id -> number of block weeks assigned
        icu_week_counts = defaultdict(int) # surgeon_id -> number of ICU weeks assigned

        for ws in week_starts:
            we = ws + timedelta(days=6)  # Sunday (Mon + 6 = Sun)

            trauma = self.trauma_surgeons()
            icu_pool = self.icu_surgeons()

            week_month = self._primary_month(ws)

            # Rank trauma surgeons: blend global fairness + monthly balance
            # Target scales with period length (10-week targets × period_scale)
            def trauma_score(s: Surgeon) -> tuple:
                target_weeks = (s.target_tregs_day or 0) * self.period_scale / 7.0
                done = block_counts[s.id]
                if target_weeks == 0:
                    return (float("inf"), float("inf"))
                global_score = done / target_weeks
                monthly_score = self._monthly_score(s, week_month)
                return (global_score, monthly_score)

            trauma_sorted = sorted(
                [s for s in trauma if self._week_available(s.id, ws, we)],
                key=trauma_score,
            )

            # Pick block1 and block2 (top 2)
            block1 = trauma_sorted[0].id if len(trauma_sorted) >= 1 else None
            block2 = trauma_sorted[1].id if len(trauma_sorted) >= 2 else None

            # Pick ICU: must be icu-capable, not block1/block2
            def icu_score(s: Surgeon) -> tuple:
                target_weeks = (s.target_icu_day or 0) * self.period_scale / 7.0
                if target_weeks == 0:
                    return (float("inf"), float("inf"))
                global_score = icu_week_counts[s.id] / target_weeks
                monthly_score = self._monthly_score(s, week_month)
                return (global_score, monthly_score)

            icu_pool_filtered = sorted(
                [
                    s for s in icu_pool
                    if s.id not in (block1, block2)
                    and self._week_available(s.id, ws, we)
                    and (s.target_icu_day or 0) > 0
                ],
                key=icu_score,
            )
            icu = icu_pool_filtered[0].id if icu_pool_filtered else None

            if block1:
                block_counts[block1] += 1
                self.monthly_credits[block1][week_month] += 7  # 7 TrEGS credits
            if block2:
                block_counts[block2] += 1
                self.monthly_credits[block2][week_month] += 7
            if icu:
                icu_week_counts[icu] += 1
                self.monthly_credits[icu][week_month] += 7  # 7 ICU credits

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
        Assign Trauma Night in 3-consecutive-day blocks wherever possible.

        Each week is divided into three night blocks:
          - FSS block : Fri + Sat + Sun  (3 nights, weekend)  → 1 surgeon
          - MTW block : Mon + Tue + Wed  (3 nights, weeknight) → 1 surgeon
          - Thu block : Thu              (1 night)             → 1 surgeon

        Priority: FSS blocks distributed equally (everyone gets ~1 per 10 wks).
        """
        trauma = self.trauma_surgeons()

        # Collect all Mon-starts for weeks that overlap with our period
        week_mons: List[date] = []
        d = self.start
        mon = d - timedelta(days=d.weekday())
        while mon <= self.end + timedelta(days=6):
            week_mons.append(mon)
            mon += timedelta(days=7)

        for week_mon in week_mons:
            # Build the three blocks for this week
            # MTW: Mon(+0), Tue(+1), Wed(+2)
            # Thu: Thu(+3)
            # FSS: Fri(+4), Sat(+5), Sun(+6)
            blocks = [
                ("mtw", [week_mon + timedelta(days=i) for i in range(3)]),   # Mon-Tue-Wed
                ("thu", [week_mon + timedelta(days=3)]),                       # Thu
                ("fss", [week_mon + timedelta(days=i) for i in range(4, 7)]), # Fri-Sat-Sun
            ]

            # Track surgeons already assigned a night block this week
            # → each surgeon can only hold ONE night block per week
            assigned_this_week: set = set()

            for block_type, days in blocks:
                # Filter to days within our schedule period
                days_in_range = [d for d in days if self.start <= d <= self.end]
                if not days_in_range:
                    continue

                target_key = "target_night_fss" if block_type == "fss" else "target_night_mth"
                shift_key = "tr_night_wknd" if block_type == "fss" else "tr_night"

                # Exclude surgeons who:
                # (a) have day shift on any day in this night block, OR
                # (b) have day shift the NEXT morning after any night in this block, OR
                # (c) already have another night block assigned this week (1 block/week rule)
                exclude: set = set(assigned_this_week)
                for d in days_in_range:
                    ds = d.isoformat()
                    sched = self.schedule.get(ds)
                    if sched:
                        exclude.add(sched.tregs_day)
                        exclude.add(sched.icu_day)
                    # Check next morning
                    next_day = d + timedelta(days=1)
                    next_sched = self.schedule.get(next_day.isoformat())
                    if next_sched:
                        exclude.add(next_sched.tregs_day)
                        exclude.add(next_sched.icu_day)
                exclude.discard(None)

                # Pick one surgeon for the entire block, respecting max_consecutive_nights
                block_len = len(days_in_range)
                eligible = [
                    s for s in trauma
                    if s.id not in exclude
                    and self.is_available(s.id, days_in_range[0])
                    and s.max_consecutive_nights >= block_len
                ]
                surgeon_id = self.pick_surgeon(
                    eligible,
                    days_in_range[0],
                    shift_key,
                    target_key,
                    exclude=exclude,
                )

                # Verify availability across all days in block; if not, pick day-by-day
                if surgeon_id and not all(
                    self.is_available(surgeon_id, d) for d in days_in_range
                ):
                    surgeon_id = None

                for d in days_in_range:
                    ds = d.isoformat()
                    day_sched = self.schedule.setdefault(ds, DaySchedule(date=ds))

                    if surgeon_id:
                        day_sched.tr_egs_sicu_night = surgeon_id
                    else:
                        # Fallback: assign individually for this day
                        excl_day = {day_sched.tregs_day, day_sched.icu_day}
                        excl_day.discard(None)
                        sid = self.pick_surgeon(trauma, d, shift_key, target_key, exclude=excl_day)
                        if sid:
                            day_sched.tr_egs_sicu_night = sid
                            self.counts[sid][shift_key] += 1

                if surgeon_id:
                    self.counts[surgeon_id][shift_key] += len(days_in_range)
                    assigned_this_week.add(surgeon_id)
                    # Record monthly credits (1 per night)
                    for nd in days_in_range:
                        self.monthly_credits[surgeon_id][nd.strftime('%Y-%m')] += 1

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
