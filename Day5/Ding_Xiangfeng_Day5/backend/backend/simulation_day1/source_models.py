"""Internal fixture manifest; NOT a replacement for the public v1 API DTOs.

These records preserve source hashes, provenance and assumption/review status.
They are not BusinessVariable evidence approvals or simulation results.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Units = Annotated[int, Field(ge=0)]


class Observation(SourceModel):
    weekStart: date
    unitsDemanded: Units
    provenance: Literal["synthetic_day1_fixture"]


class HistoricalDemand(SourceModel):
    dataVersion: Literal["demo-2026.10.04-v4"]
    sourceFile: Literal["public/demo/historical_demand.csv"]
    sourceSha256: Sha256
    provenance: Literal["synthetic_day1_fixture"]
    weekCount: Literal[104]
    totalUnits: Units
    meanWeeklyUnits: Annotated[float, Field(ge=0)]
    lockedForecastUnits24m: Units
    lockedForecastProvenance: str
    observations: Annotated[list[Observation], Field(min_length=104, max_length=104)]

    @model_validator(mode="after")
    def totals_and_continuity(self):
        rows = self.observations
        if rows[0].weekStart != date(2024, 10, 7) or any(row.weekStart != rows[0].weekStart + timedelta(weeks=i) for i, row in enumerate(rows)):
            raise ValueError("missing/duplicate historical week")
        if self.totalUnits != sum(row.unitsDemanded for row in rows) or abs(self.meanWeeklyUnits - self.totalUnits / 104) > 1e-9:
            raise ValueError("historical-demand aggregates inconsistent")
        return self


class SupplierOrder(SourceModel):
    orderId: str
    supplier: Literal["A", "B"]
    orderDate: date
    arrivalDate: date
    units: Units
    basePriceUsd: Annotated[float, Field(ge=0)]
    provenance: Literal["synthetic_day1_fixture"]

    @model_validator(mode="after")
    def positive_lead(self):
        if self.arrivalDate < self.orderDate:
            raise ValueError("supplier arrival predates order")
        return self


class DeliveryHistory(SourceModel):
    sourceFile: Literal["public/demo/supplier_delivery_history.xlsx"]
    sourceSha256: Sha256
    orderCount: Literal[48]
    orders: Annotated[list[SupplierOrder], Field(min_length=48, max_length=48)]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({r.orderId for r in self.orders}) != 48:
            raise ValueError("duplicate PO IDs")
        return self


class OpeningInventory(SourceModel):
    sourceFile: Literal["public/demo/opening_inventory.csv"]
    sourceSha256: Sha256
    asOfDate: date
    sku: str
    unitsOnHand: Units
    provenance: Literal["synthetic_day1_fixture"]


class NoticeEntry(SourceModel):
    date: date
    channel: str
    recipient: str
    event: str
    validWrittenNonrenewalNotice: bool
    provenance: Literal["synthetic_mock_not_a_real_supplier_record"]


class NoticeRegister(SourceModel):
    sourceFile: Literal["public/demo/supplier_correspondence_log.csv"]
    sourceSha256: Sha256
    noticeSent: bool
    entries: Annotated[list[NoticeEntry], Field(min_length=1)]

    @model_validator(mode="after")
    def register_status(self):
        if self.noticeSent != any(e.validWrittenNonrenewalNotice for e in self.entries):
            raise ValueError("noticeSent differs from explicit synthetic register")
        return self


class ContractAssumptions(SourceModel):
    sourceFile: Literal["public/demo/supplier_a_agreement.pdf"]
    sourceSha256: Sha256
    evidencePage: Literal[4]
    forecastBasis: Literal["locked-at-renewal"]
    lockedForecastUnits24m: Literal[26000]
    forecastSource: str
    humanReviewed: Literal[False]
    status: Literal["quote_matched_synthetic_not_human_reviewed"]


class DemoInputs(SourceModel):
    dataVersion: Literal["demo-2026.10.04-v4"]
    fixtureStatus: Literal["synthetic_local_mock_not_engine_input_verified"]
    historicalDemand: HistoricalDemand
    supplierDelivery: DeliveryHistory
    openingInventory: OpeningInventory
    noticeRegister: NoticeRegister
    contractAssumptions: ContractAssumptions

    @model_validator(mode="after")
    def separate_forecast_and_history(self):
        if self.historicalDemand.dataVersion != self.dataVersion or self.historicalDemand.lockedForecastUnits24m != self.contractAssumptions.lockedForecastUnits24m:
            raise ValueError("dataset version or locked-forecast mismatch")
        return self
