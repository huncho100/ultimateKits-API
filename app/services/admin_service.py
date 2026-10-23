from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.statuses import ADMIN_SETTABLE_STATUSES, ORDER_STATUS_TRANSITIONS, PaymentStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.schemas.admin import (
    AdminCustomer,
    AdminCustomerPage,
    AdminOrderDetail,
    AdminOrderPage,
    AdminOverview,
    InventorySummary,
    SalesSummary,
)


LOW_STOCK_THRESHOLD = 5


def verified_payment():
    # EXISTS counts each order once, even if it has multiple successful attempts.
    return (
        (Payment.order_id == Order.id)
        & (Payment.user_id == Order.user_id)
        & (Payment.status == PaymentStatus.SUCCESS)
        & (Payment.currency == "NGN")
        & (Payment.provider == "paystack")
        & (Payment.amount == Order.total_amount)
    )


def has_verified_payment(db: Session):
    return db.query(Payment.id).filter(verified_payment()).exists()


def order_query(db: Session):
    return db.query(Order).options(
        selectinload(Order.user),
        selectinload(Order.payments),
        selectinload(Order.items).selectinload(OrderItem.product),
    )


def order_detail(order: Order) -> AdminOrderDetail:
    verified = any(
        p.status == PaymentStatus.SUCCESS
        and p.provider == "paystack"
        and p.currency == "NGN"
        and p.amount == order.total_amount
        and p.user_id == order.user_id
        for p in order.payments
    )
    payments = sorted(order.payments, key=lambda p: p.id, reverse=True)
    payment_status = (
        "success" if verified else
        ("inconsistent" if payments[0].status == "success" else payments[0].status)
        if payments else "not_started"
    )
    return AdminOrderDetail(
        **{
            field: getattr(order, field)
            for field in (
                "id", "user_id", "status", "total_amount",
                "created_at", "updated_at", "items",
            )
        },
        customer=order.user,
        payment_status=payment_status,
        payments=payments,
        available_actions=sorted(
            ORDER_STATUS_TRANSITIONS.get(order.status, frozenset())
            & ADMIN_SETTABLE_STATUSES
        ),
        product_names={
            item.product_id: item.product.name
            for item in order.items if item.product is not None
        },
    )


class AdminService:
    @staticmethod
    def overview(db: Session) -> AdminOverview:
        available = (
            Product.in_stock.is_(True)
            & or_(Product.stock_quantity.is_(None), Product.stock_quantity > 0)
        )
        verified = db.query(Order).filter(has_verified_payment(db))
        completed = verified.filter(Order.status != "cancelled")
        cancelled = verified.filter(Order.status == "cancelled")
        return AdminOverview(
            inventory=InventorySummary(
                total=db.query(Product).count(),
                in_stock=db.query(Product).filter(available).count(),
                low_stock=db.query(Product).filter(
                    available, Product.stock_quantity.between(1, LOW_STOCK_THRESHOLD)
                ).count(),
                out_of_stock=db.query(Product).filter(~available).count(),
                uncounted=db.query(Product).filter(Product.stock_quantity.is_(None)).count(),
                low_stock_threshold=LOW_STOCK_THRESHOLD,
            ),
            total_orders=db.query(Order).count(),
            awaiting_processing=completed.filter(Order.status == "paid").count(),
            sales=SalesSummary(
                verified_orders=completed.count(),
                verified_sales_ngn=completed.with_entities(
                    func.coalesce(func.sum(Order.total_amount), 0)
                ).scalar() or Decimal("0.00"),
                cancelled_verified_orders=cancelled.count(),
                cancelled_verified_ngn=cancelled.with_entities(
                    func.coalesce(func.sum(Order.total_amount), 0)
                ).scalar() or Decimal("0.00"),
            ),
            recent_orders=[
                order_detail(order) for order in order_query(db)
                .order_by(Order.created_at.desc(), Order.id.desc()).limit(5).all()
            ],
        )

    @staticmethod
    def orders(
        db: Session, *, page: int, page_size: int, q: str | None,
        status: str | None, payment_status: str | None, customer_id: int | None,
    ) -> AdminOrderPage:
        query = order_query(db).join(User)
        if q:
            term = q.strip()
            matches = [
                User.email.icontains(term, autoescape=True),
                User.first_name.icontains(term, autoescape=True),
                User.last_name.icontains(term, autoescape=True),
                Order.payments.any(Payment.reference.icontains(term, autoescape=True)),
            ]
            if term.removeprefix("#").isdigit():
                matches.append(Order.id == int(term.removeprefix("#")))
            query = query.filter(or_(*matches))
        if status:
            query = query.filter(Order.status == status)
        if payment_status == "verified":
            query = query.filter(has_verified_payment(db))
        elif payment_status == "unverified":
            query = query.filter(~has_verified_payment(db))
        if customer_id is not None:
            query = query.filter(Order.user_id == customer_id)
        total = query.count()
        orders = query.order_by(Order.created_at.desc(), Order.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        return AdminOrderPage(
            items=[order_detail(order) for order in orders],
            total=total, page=page, page_size=page_size,
        )

    @staticmethod
    def customers(db: Session, *, page: int, page_size: int, q: str | None):
        query = db.query(User).filter(User.role == "customer")
        if q:
            query = query.filter(or_(*(
                column.icontains(q.strip(), autoescape=True)
                for column in (User.email, User.first_name, User.last_name)
            )))
        total = query.count()
        customers = query.order_by(User.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        counts = dict(db.query(Order.user_id, func.count(Order.id)).filter(
            Order.user_id.in_([user.id for user in customers])
        ).group_by(Order.user_id).all())
        return AdminCustomerPage(
            items=[
                AdminCustomer(
                    **{
                        field: getattr(user, field) for field in (
                            "id", "first_name", "last_name", "email", "is_active",
                        )
                    },
                    order_count=counts.get(user.id, 0),
                ) for user in customers
            ],
            total=total, page=page, page_size=page_size,
        )
