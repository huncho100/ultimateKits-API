from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemCreate, CartItemUpdate


class CartService:
    # ==========================================
    # Get Or Create Cart
    # ==========================================

    @staticmethod
    def get_or_create_cart(
        db: Session,
        user_id: int,
    ) -> Cart:
        """
        Retrieve the user's cart.

        If the user does not have a cart yet,
        create one.
        """

        cart = (
            db.query(Cart)
            .filter(Cart.user_id == user_id)
            .first()
        )

        if cart is None:
            cart = Cart(
                user_id=user_id,
            )

            db.add(cart)
            db.commit()
            db.refresh(cart)

        return cart

    # ==========================================
    # Get Cart
    # ==========================================

    @staticmethod
    def get_cart(
        db: Session,
        user_id: int,
    ) -> Cart:
        """
        Retrieve the user's cart.

        Creates an empty cart if one does not exist.
        """

        return CartService.get_or_create_cart(
            db,
            user_id,
        )

    # ==========================================
    # Add Item To Cart
    # ==========================================

    @staticmethod
    def add_item(
        db: Session,
        cart: Cart,
        data: CartItemCreate,
    ) -> CartItem:
        """
        Add a product to the cart.

        If the product already exists in the cart,
        increase its quantity instead of creating
        a duplicate cart item.
        """

        # ------------------------------------------
        # Find Product
        # ------------------------------------------

        product = (
            db.query(Product)
            .filter(Product.id == data.product_id)
            .first()
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        # ------------------------------------------
        # Check Stock
        # ------------------------------------------

        if not product.in_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is out of stock.",
            )

        # ------------------------------------------
        # Check Existing Cart Item
        # ------------------------------------------

        cart_item = (
            db.query(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == data.product_id,
            )
            .first()
        )

        if cart_item:
            cart_item.quantity += data.quantity
        else:
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=data.quantity,
            )

            db.add(cart_item)

        db.commit()
        db.refresh(cart_item)

        return cart_item

    # ==========================================
    # Update Cart Item
    # ==========================================

    @staticmethod
    def update_item(
        db: Session,
        cart: Cart,
        item_id: int,
        data: CartItemUpdate,
    ) -> CartItem:
        """
        Update the quantity of an existing cart item.
        """

        cart_item = (
            db.query(CartItem)
            .filter(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id,
            )
            .first()
        )

        if cart_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        cart_item.quantity = data.quantity

        db.commit()
        db.refresh(cart_item)

        return cart_item

    # ==========================================
    # Remove Cart Item
    # ==========================================

    @staticmethod
    def remove_item(
        db: Session,
        cart: Cart,
        item_id: int,
    ) -> None:
        """
        Remove an item from the user's cart.
        """

        cart_item = (
            db.query(CartItem)
            .filter(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id,
            )
            .first()
        )

        if cart_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        db.delete(cart_item)
        db.commit()

    # ==========================================
    # Clear Cart
    # ==========================================

    @staticmethod
    def clear_cart(
        db: Session,
        cart: Cart,
    ) -> None:
        """
        Remove every item from the user's cart.
        """

        (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id)
            .delete(
                synchronize_session=False,
            )
        )

        db.commit()

    # ==========================================
    # Calculate Cart Total
    # ==========================================

    @staticmethod
    def calculate_total(
        cart: Cart,
    ) -> Decimal:
        """
        Calculate the current total value of the cart.
        """

        total = Decimal("0.00")

        for item in cart.items:
            total += (
                item.product.price
                * item.quantity
            )

        return total.quantize(
            Decimal("0.01")
        )