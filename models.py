from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RiskNode:
    id: int
    name: str
    prob: float = 0.0
    loss_min: float = 0.0
    loss_max: float = 0.0
    severity: float = 1.0
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)
