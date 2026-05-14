from pydantic import BaseModel


class GuestResponse(BaseModel):
    id: str
    hotel_id: str
    first_name: str | None = None
    last_name: str | None = None
    doc_type: str | None = None
    doc_country: str | None = None
    doc_number_last4: str | None = None
    nationality: str | None = None
    created_at: str
    deleted_at: str | None = None


class GuestListItem(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    doc_type: str | None = None
    doc_number_last4: str | None = None
    created_at: str
