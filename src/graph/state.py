from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompanyState:
    ticker: str
    company_name: str


@dataclass
class AgentState:
    companies: list[CompanyState] = field(default_factory=list)
    current_step: str = ""
