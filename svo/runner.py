from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
	root_dir = Path(__file__).resolve().parent.parent
	if str(root_dir) not in sys.path:
		sys.path.insert(0, str(root_dir))

	from runner import main as root_main

	return root_main(argv)


if __name__ == "__main__":
	sys.exit(main())
