"""Shared Pydantic contracts between agents, tools, and services."""

from app.schemas.company import CompanyProfile, ManagementSummary, MoatAssessment
from app.schemas.competitors import CompetitorAnalysis
from app.schemas.evidence import BundleStatus, Evidence, EvidenceBundle
from app.schemas.financials import FinancialMetrics, RevenueHistory, RiskFactors
from app.schemas.news import NewsSummary
from app.schemas.phase0 import (
    PHASE0_DISCLAIMER,
    Phase0Result,
    Phase0Status,
    assert_claims_cite_bundle,
)
from app.schemas.report import (
    InvestmentThesis,
    ResearchReport,
    Scorecard,
    ThesisClaim,
)
from app.schemas.ticker import InvalidTickerError, normalize_ticker

__all__ = [
    "PHASE0_DISCLAIMER",
    "BundleStatus",
    "CompanyProfile",
    "CompetitorAnalysis",
    "Evidence",
    "EvidenceBundle",
    "FinancialMetrics",
    "InvalidTickerError",
    "InvestmentThesis",
    "ManagementSummary",
    "MoatAssessment",
    "NewsSummary",
    "Phase0Result",
    "Phase0Status",
    "ResearchReport",
    "RevenueHistory",
    "RiskFactors",
    "Scorecard",
    "ThesisClaim",
    "assert_claims_cite_bundle",
    "normalize_ticker",
]
