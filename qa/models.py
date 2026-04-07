from dataclasses import dataclass


@dataclass
class Finding:
    filename: str
    line_number: int
    severity: str  # "critical" | "medium" | "low"
    title: str
    explanation: str
    suggestion: str
