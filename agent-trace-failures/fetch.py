"""Download everything the analysis reads into data/ (about 27 MB, not committed).

    python fetch.py

The traces are Sierra's own leaderboard run of GPT-5 on tau2-bench, taken from
the public bucket behind taubench.com. They are not redistributed here: this
repository holds only trace ids, the coded sheet and the code.
"""

import pathlib
import urllib.request

DATA = pathlib.Path(__file__).parent / "data"

# Pinned so the task comparison is reproducible.
RUN_COMMIT = "964ef7aed331ecf0c9bc592abdc2b4aecd941586"     # tau2-bench at the time of the GPT-5 run
SIERRA_COMMIT = "5bfa7e37b36656b37dc6d022156be6563c1007f3"  # tau2-bench main, 2026-09-28
AMAZON_COMMIT = "864350a8971a8f8ee9e7b8472e2edc380a806b0c"  # tau2-bench-verified main, 2026-04-02

BUCKET = "https://sierra-tau-bench-public.s3.amazonaws.com/submissions/gpt-5_sierra_2025-08-09/trajectories"
SIERRA = "https://raw.githubusercontent.com/sierra-research/tau2-bench"
AMAZON = "https://raw.githubusercontent.com/amazon-agi/tau2-bench-verified"

FILES = {}
for dom in ("airline", "retail"):
    FILES[f"traces_{dom}.json"] = f"{BUCKET}/gpt-5_{dom}_default_gpt-4.1-2025-04-14_4trials.json"
    FILES[f"tools_{dom}.py"] = f"{SIERRA}/{RUN_COMMIT}/src/tau2/domains/{dom}/tools.py"
    FILES[f"tasks_sierra_{dom}.json"] = f"{SIERRA}/{SIERRA_COMMIT}/data/tau2/domains/{dom}/tasks.json"
    FILES[f"tasks_amazon_{dom}.json"] = f"{AMAZON}/{AMAZON_COMMIT}/data/tau2/domains/{dom}/tasks.json"
FILES["FIXES_amazon.md"] = f"{AMAZON}/{AMAZON_COMMIT}/FIXES.md"


def main():
    DATA.mkdir(exist_ok=True)
    total = 0
    for name, url in FILES.items():
        path = DATA / name
        if not path.exists():
            print(f"fetching {name}")
            tmp = path.with_suffix(path.suffix + ".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(path)
        total += path.stat().st_size
    print(f"{len(FILES)} files in {DATA}, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
