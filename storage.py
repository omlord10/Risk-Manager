import json
from typing import Dict
from models import RiskNode

DATA_FILE = "data/nodes.json"

def save_nodes(nodes: Dict[int, RiskNode]):
    serializable = {nid: node.__dict__ for nid, node in nodes.items()}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=4)

def load_nodes() -> Dict[int, RiskNode]:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return {int(nid): RiskNode(**ndata) for nid, ndata in raw.items()}
    except FileNotFoundError:
        return {}
