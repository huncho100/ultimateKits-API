from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Admin Order Status Update
# ==========================================


class AdminOrderStatusUpdate(BaseModel):
    """
    Data required for an administrator to
    update an order's status.
    """

    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )


# ==========================================
# Admin Order Status Response
# ==========================================


class AdminOrderStatusResponse(BaseModel):
    """
    Response returned after an administrator
    updates an order's status.
    """

    id: int
    user_id: int
    status: str

    model_config = ConfigDict(
        from_attributes=True,
    )