from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedSubmissionItem:
    category: str
    goal_id: int
    # TODO: unify the type of value to Optional[int]
    value: None | int | bool
    submission_time: datetime
