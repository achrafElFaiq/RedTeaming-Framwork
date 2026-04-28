from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_FRAMEWORKS_DIR = PROJECT_ROOT / "frameworks"

if str(PROJECT_FRAMEWORKS_DIR) not in __path__:
	__path__.append(str(PROJECT_FRAMEWORKS_DIR))

