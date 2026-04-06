"""
Data models for the surgeon call schedule system.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
from pathlib import Path


class ShiftType(str, Enum):
    TREGS_DAY = "TrEGS Day"      # Trauma/EGS day shift (7a-530p)
    ICU_DAY = "ICU Day"           # ICU day shift (7a-530p)
    TR_EGS_SICU_NIGHT = "Tr/EGS/SICU N"  # Trauma/EGS/SICU night (530p-7a)
    TR_DAY_BACKUP = "Tr Day b/u"  # Trauma day backup
    TR_NIGHT_BACKUP = "Tr Night b/u"  # Trauma night backup


class DayOfWeek(int, Enum):
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6


@dataclass
class Surgeon:
    id: str                      # e.g. "furuta"
    name: str                    # Display name e.g. "Furuta"
    fte: float                   # 0.6, 0.75, 0.9, 1.0
    can_do_trauma: bool = True
    can_do_icu: bool = True
    # Per-10-week shift targets (auto-calculated if None)
    target_tregs_day: Optional[int] = None
    target_icu_day: Optional[int] = None
    target_night_mth: Optional[int] = None   # Mon-Thu nights
    target_night_fss: Optional[int] = None   # Fri-Sat-Sun nights
    # Shift adjustment per 4 weeks / month (e.g. Furuta = -2)
    shift_adjust: int = 0
    # Max consecutive Tr Night shifts (3 = standard FSS/MTW block)
    max_consecutive_nights: int = 3
    notes: str = ""

    @property
    def total_shifts_per_10wk(self) -> int:
        base = round(self.fte * 14)
        return max(0, base + self.shift_adjust)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "fte": self.fte,
            "can_do_trauma": self.can_do_trauma,
            "can_do_icu": self.can_do_icu,
            "target_tregs_day": self.target_tregs_day,
            "target_icu_day": self.target_icu_day,
            "target_night_mth": self.target_night_mth,
            "target_night_fss": self.target_night_fss,
            "shift_adjust": self.shift_adjust,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Surgeon":
        d = dict(d)
        d.pop("icu_only", None)  # removed field; use can_do_trauma=False instead
        return cls(**d)


@dataclass
class PTORequest:
    surgeon_id: str
    date: str           # ISO format "2026-03-15"
    reason: str = ""

    def to_dict(self):
        return {"surgeon_id": self.surgeon_id, "date": self.date, "reason": self.reason}

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class ShiftPreference:
    """A surgeon's preference for a specific shift type / date range."""
    surgeon_id: str
    shift_type: Optional[ShiftType]    # None = any
    preferred: bool                    # True = want, False = avoid
    date_from: Optional[str] = None    # ISO date, None = whole period
    date_to: Optional[str] = None
    day_of_week: Optional[int] = None  # 0=Mon..6=Sun, None = any
    notes: str = ""

    def to_dict(self):
        return {
            "surgeon_id": self.surgeon_id,
            "shift_type": self.shift_type.value if self.shift_type else None,
            "preferred": self.preferred,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "day_of_week": self.day_of_week,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        if d.get("shift_type"):
            d["shift_type"] = ShiftType(d["shift_type"])
        return cls(**d)


@dataclass
class DaySchedule:
    """The complete schedule for one day."""
    date: str                   # ISO "2026-03-01"
    tregs_day: Optional[str] = None         # surgeon id
    tregs_day_office: Optional[str] = None  # surgeon with office hours that day
    block1: Optional[str] = None            # week block surgeon 1
    block2: Optional[str] = None            # week block surgeon 2
    icu_day: Optional[str] = None
    tr_egs_sicu_night: Optional[str] = None   # Tr/EGS/SICU Night (was tr_night + egs_icu_night)
    tr_day_backup: Optional[str] = None
    tr_night_backup: Optional[str] = None
    notes: str = ""             # e.g. "UH Gr Rds, M&M"

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        import dataclasses
        d = dict(d)
        # Migrate old field names
        if "tr_night" in d and "tr_egs_sicu_night" not in d:
            d["tr_egs_sicu_night"] = d.pop("tr_night")
        # Remove any keys not in the current dataclass
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**d)


@dataclass
class WeekBlock:
    """One week's block assignments."""
    week_start: str     # ISO date of Sunday
    block1_surgeon: str
    block2_surgeon: str
    icu_surgeon: str

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
