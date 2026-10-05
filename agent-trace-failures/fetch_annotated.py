"""Download the human-annotated failure datasets into data/annotated/ (about 11 MB, not committed).

    python fetch_annotated.py       # the Who&When step needs pyarrow to read two parquet files

AgentRx (Microsoft, MIT): https://github.com/microsoft/AgentRx
Who&When (Zhang et al. 2025): https://huggingface.co/datasets/Kevin355/Who_and_When
"""

import json
import urllib.request

from traces import DATA

OUT = DATA / "annotated"
AGENTRX = "https://raw.githubusercontent.com/microsoft/AgentRx/main/data"
AGENTRX_TREE = "https://api.github.com/repos/microsoft/AgentRx/git/trees/main?recursive=1"
WHOWHEN = "https://huggingface.co/datasets/Kevin355/Who_and_When/resolve/main"


def get(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)


def main():
    for name in ("ground_truth/magentic_one_ground_truth.json", "ground_truth/tau_ground_truth.json",
                 "tau_retail/tau_dataset_failed.json", "policies/retail_policy.txt"):
        get(f"{AGENTRX}/{name}", OUT / "agentrx" / name.split("/")[1])
    with urllib.request.urlopen(AGENTRX_TREE) as res:
        tree = json.load(res)["tree"]
    for entry in tree:
        if entry["path"].startswith("data/magentic_dataset/") and entry["path"].endswith(".json"):
            name = entry["path"].split("/")[-1]
            get(f"{AGENTRX}/magentic_dataset/{name}", OUT / "agentrx" / "magentic" / name)

    import pyarrow.parquet as pq
    for name in ("Hand-Crafted", "Algorithm-Generated"):
        target = OUT / "whowhen" / f"{name}.json"
        if not target.exists():
            parquet = OUT / "whowhen" / f"{name}.parquet"
            get(f"{WHOWHEN}/{name}.parquet", parquet)
            target.write_text(json.dumps(pq.read_table(parquet).to_pylist(), default=str))
            parquet.unlink()
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"annotated datasets in {OUT}, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
