"""
Seed the database with surgeon data from the 10-week block breakdown PDF.
Run once: python3 -m scheduler.seed_data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler.models import Surgeon
from scheduler.data_store import save_surgeons, load_surgeons

SURGEONS = [
    Surgeon(
        id="brito",
        name="Brito",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=14,
        target_icu_day=7,
        target_night_mth=6,
        target_night_fss=3,
    ),
    Surgeon(
        id="carlton",
        name="Carlton",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=14,
        target_icu_day=7,
        target_night_mth=4,
        target_night_fss=3,
    ),
    Surgeon(
        id="eischen",
        name="Eischen",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=14,
        target_icu_day=7,
        target_night_mth=5,
        target_night_fss=3,
    ),
    Surgeon(
        id="furuta",
        name="Furuta",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=False,   # trauma only
        shift_adjust=-2,
        target_tregs_day=21,
        target_icu_day=0,
        target_night_mth=4,
        target_night_fss=3,
    ),
    Surgeon(
        id="hayashi",
        name="Hayashi",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=False,   # trauma only
        target_tregs_day=21,
        target_icu_day=0,
        target_night_mth=4,
        target_night_fss=3,
    ),
    Surgeon(
        id="inouye",
        name="Inouye",
        fte=0.9,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=7,
        target_icu_day=14,  # heavy ICU
        target_night_mth=0,
        target_night_fss=3,
    ),
    Surgeon(
        id="musika",
        name="Musika",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=14,
        target_icu_day=7,
        target_night_mth=6,
        target_night_fss=3,
    ),
    Surgeon(
        id="ra",
        name="Ra",
        fte=0.6,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=7,
        target_icu_day=7,
        target_night_mth=2,
        target_night_fss=3,
    ),
    Surgeon(
        id="salotto",
        name="Salotto",
        fte=0.75,
        can_do_trauma=True,
        can_do_icu=False,
        target_tregs_day=14,
        target_icu_day=0,
        target_night_mth=4,
        target_night_fss=3,
    ),
    Surgeon(
        id="yong",
        name="Yong",
        fte=1.0,
        can_do_trauma=True,
        can_do_icu=True,
        target_tregs_day=14,
        target_icu_day=7,
        target_night_mth=5,
        target_night_fss=3,
    ),
    Surgeon(
        id="takanishi",
        name="Takanishi",
        fte=0.0,
        can_do_trauma=False,
        can_do_icu=True,
        target_tregs_day=0,
        target_icu_day=14,
        target_night_mth=0,
        target_night_fss=0,
        notes="ICU-only role. Not in trauma call pool.",
    ),
]


def seed():
    existing = load_surgeons()
    if existing:
        print(f"Already have {len(existing)} surgeons. Skipping seed.")
        return
    save_surgeons(SURGEONS)
    print(f"Seeded {len(SURGEONS)} surgeons.")


if __name__ == "__main__":
    seed()
