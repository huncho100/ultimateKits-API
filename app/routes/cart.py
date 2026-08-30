from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.cart import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartResponse,
)
from app.services.cart_service import CartService


router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


# ==========================================
# Get Current User's Cart
# ==========================================

@router.get(
    "",
    response_model=CartResponse,
)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the authenticated user's cart.
    """

    return CartService.get_cart(
        db,
        current_user.id,
    )


# ==========================================
# Add Item To Cart
# ==========================================

@router.post(
    "/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cart_item(
    data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a product to the authenticated user's cart.
    """

    cart = CartService.get_cart(
        db,
        current_user.id,
    )

    return CartService.add_item(
        db,
        cart,
        data,
    )


# ==========================================
# Update Cart Item
# ==========================================

@router.patch(
    "/items/{item_id}",
    response_model=CartItemResponse,
)
def update_cart_item(
    item_id: int,
    data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the quantity of an item in the
    authenticated user's cart.
    """

    cart = CartService.get_cart(
        db,
        current_user.id,
    )

    return CartService.update_item(
        db,
        cart,
        item_id,
        data,
    )


# ==========================================
# Remove Cart Item
# ==========================================

@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an item from the authenticated user's cart.
    """

    cart = CartService.get_cart(
        db,
        current_user.id,
    )

    CartService.remove_item(
        db,
        cart,
        item_id,
    )

    return None


# ==========================================
# Clear Cart
# ==========================================

@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove all items from the authenticated user's cart.
    """

    cart = CartService.get_cart(
        db,
        current_user.id,
    )

    CartService.clear_cart(
        db,
        cart,
    )

    return None