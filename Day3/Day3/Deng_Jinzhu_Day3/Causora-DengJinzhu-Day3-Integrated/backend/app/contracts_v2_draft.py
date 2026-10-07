"""Compatibility exports for the former v2-draft module.

The release-gated endpoint now validates against `app.contracts_v2`; this file
keeps earlier tests/imports working without maintaining a divergent DTO.
"""
from app.contracts_v2 import (  # noqa: F401
    ApiSuccessV2 as ApiSuccessV2Draft,
    CashP90Basis,
    FormulaComponent,
    FormulaTrace,
    RoundingAudit,
    SamplePath,
    ServiceLevelBasis,
    SimulateResponseV2 as SimulateResponseV2Draft,
    StockoutProbabilityBasis,
    TRACE_SCHEMA_VERSION,
    TraceParameter,
    TraceProvenance,
    TraceRunIdentity,
    V2_VERSION,
)
