from typing import Literal

from pydantic import BaseModel

AnonymizeStatus = Literal["anonymized", "already_anonymized"]


class AnonymizeVisitorResponse(BaseModel):
    status: AnonymizeStatus
