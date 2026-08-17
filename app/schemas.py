from typing import List, Optional

from pydantic import BaseModel, Field


class PenaltyItem(BaseModel):
    description: str = Field(description="За что предусмотрен штраф или неустойка")
    amount: Optional[str] = Field(None, description="Размер штрафа (сумма, процент и т.п.)")


class TenderSummary(BaseModel):
    contract_amount: Optional[str] = Field(None, description="Сумма контракта с указанием валюты")
    deadline: Optional[str] = Field(None, description="Сроки выполнения работ/услуг")
    key_requirements: List[str] = Field(
        default_factory=list, description="Ключевые требования к исполнителю"
    )
    penalties: List[PenaltyItem] = Field(
        default_factory=list, description="Штрафы и неустойки за нарушение условий контракта"
    )
    summary: str = Field(description="Краткая выжимка документа (2-4 предложения)")
