"""
JSON-based local data storage.
"""
import json
from pathlib import Path
from typing import List, Optional
from .models import Surgeon, PTORequest, ShiftPreference, DaySchedule, WeekBlock

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SURGEONS_FILE = DATA_DIR / "surgeons.json"
PTO_FILE = DATA_DIR / "pto_requests.json"
PREFS_FILE = DATA_DIR / "preferences.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
BLOCKS_FILE = DATA_DIR / "week_blocks.json"


def _load(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save(path: Path, data: list):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# --- Surgeons ---

def load_surgeons() -> List[Surgeon]:
    return [Surgeon.from_dict(d) for d in _load(SURGEONS_FILE)]


def save_surgeons(surgeons: List[Surgeon]):
    _save(SURGEONS_FILE, [s.to_dict() for s in surgeons])


def get_surgeon(surgeon_id: str) -> Optional[Surgeon]:
    for s in load_surgeons():
        if s.id == surgeon_id:
            return s
    return None


# --- PTO ---

def load_pto() -> List[PTORequest]:
    return [PTORequest.from_dict(d) for d in _load(PTO_FILE)]


def save_pto(requests: List[PTORequest]):
    _save(PTO_FILE, [r.to_dict() for r in requests])


def get_pto_for_surgeon(surgeon_id: str) -> List[PTORequest]:
    return [r for r in load_pto() if r.surgeon_id == surgeon_id]


# --- Preferences ---

def load_preferences() -> List[ShiftPreference]:
    return [ShiftPreference.from_dict(d) for d in _load(PREFS_FILE)]


def save_preferences(prefs: List[ShiftPreference]):
    _save(PREFS_FILE, [p.to_dict() for p in prefs])


def get_prefs_for_surgeon(surgeon_id: str) -> List[ShiftPreference]:
    return [p for p in load_preferences() if p.surgeon_id == surgeon_id]


# --- Schedule ---

def load_schedule() -> List[DaySchedule]:
    return [DaySchedule.from_dict(d) for d in _load(SCHEDULE_FILE)]


def save_schedule(schedule: List[DaySchedule]):
    _save(SCHEDULE_FILE, [d.to_dict() for d in schedule])


def load_week_blocks() -> List[WeekBlock]:
    return [WeekBlock.from_dict(d) for d in _load(BLOCKS_FILE)]


def save_week_blocks(blocks: List[WeekBlock]):
    _save(BLOCKS_FILE, [b.to_dict() for b in blocks])
