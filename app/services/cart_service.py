from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.inventory_service import InventoryService


def _reject_excess_quantity(quantity: int) -> None:
    """
    Reject a quantity above the per-product ceiling.

    Schema validation bounds a single request, but a cart
    accumulates: repeated adds, or the same product listed
    twice in one sync, can build a quantity no individual
    request ever asked for. The limit has to be applied to
    the resulting total, not just the increment.
    """

    if quantity > settings.MAX_CART_ITEM_QUANTITY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Quantity per product cannot exceed "
                f"{settings.MAX_CART_ITEM_QUANTITY}."
            ),
        )


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

        resulting_quantity = (
            cart_item.quantity + data.quantity
            if cart_item
            else data.quantity
        )

        # ------------------------------------------
        # Check Limits
        # ------------------------------------------

        # Both limits apply to what the cart would end up
        # holding, not to the increment, because repeated
        # adds accumulate.

        _reject_excess_quantity(resulting_quantity)

        InventoryService.assert_available(
            product,
            resulting_quantity,
        )

        if cart_item:
            cart_item.quantity = resulting_quantity
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

        # The product can have sold out, or been reduced,
        # since it was put in the cart.

        if cart_item.product is not None:
            InventoryService.assert_available(
                cart_item.product,
                data.quantity,
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
    # Discard Items For User
    # ==========================================

    @staticmethod
    def discard_items_for_user(
        db: Session,
        user_id: int,
    ) -> None:
        """
        Empty a user's cart without committing.

        Unlike clear_cart this leaves the transaction open.
        The settlement path calls it part-way through writing
        a payment result, and the cart emptying has to land in
        the same commit as the order becoming paid rather than
        in one of its own.

        Does nothing if the user has no cart.
        """

        cart = (
            db.query(Cart)
            .filter(Cart.user_id == user_id)
            .first()
        )

        if cart is None:
            return

        (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id)
            .delete(
                synchronize_session=False,
            )
        )

        db.expire(cart, ["items"])

    # ==========================================
    # Synchronize Cart
    # ==========================================

    @staticmethod
    def sync_cart(
        db: Session,
        cart: Cart,
        items: list[CartItemCreate],
    ) -> Cart:
        """
        Atomically replace a cart with the supplied items.
        """

        quantities: dict[int, int] = {}

        for item in items:
            quantities[item.product_id] = (
                quantities.get(item.product_id, 0)
                + item.quantity
            )

        for quantity in quantities.values():
            _reject_excess_quantity(quantity)

        products = (
            db.query(Product)
            .filter(Product.id.in_(quantities))
            .all()
            if quantities
            else []
        )
        products_by_id = {
            product.id: product
            for product in products
        }

        missing_ids = (
            set(quantities) - set(products_by_id)
        )

        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Products not found: "
                    + ", ".join(
                        str(product_id)
                        for product_id in sorted(missing_ids)
                    )
                ),
            )

        unavailable_ids = [
            product_id
            for product_id, product
            in products_by_id.items()
            if not product.in_stock
        ]

        if unavailable_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Products out of stock: "
                    + ", ".join(
                        str(product_id)
                        for product_id in sorted(unavailable_ids)
                    )
                ),
            )

        # Counted products additionally have to have enough
        # on the shelf for the quantity being asked for.

        shortfalls: list[str] = []

        for product_id, quantity in sorted(
            quantities.items()
        ):
            available = (
                InventoryService.available_quantity(
                    products_by_id[product_id],
                )
            )

            if available is not None and quantity > available:
                shortfalls.append(
                    f"{product_id} (only {available} left)"
                )

        if shortfalls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Insufficient stock: "
                    + ", ".join(shortfalls)
                ),
            )

        try:
            (
                db.query(CartItem)
                .filter(CartItem.cart_id == cart.id)
                .delete(synchronize_session=False)
            )

            for product_id, quantity in quantities.items():
                db.add(
                    CartItem(
                        cart_id=cart.id,
                        product_id=product_id,
                        quantity=quantity,
                    )
                )

            db.commit()
            db.expire(cart, ["items"])
            return cart
        except Exception:
            db.rollback()
            raise

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