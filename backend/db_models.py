from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    orders: Mapped[list["OrderTable"]] = relationship(back_populates="user")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
    )


class ItemTable(Base):
    __tablename__ = "items"

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[str] = mapped_column(String(120), nullable=False)
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    videos: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    order_details: Mapped[list["OrderDetailTable"]] = relationship(back_populates="item")


class OrderTable(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    order_status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    order_date: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped[UserTable] = relationship(back_populates="orders")
    order_details: Mapped[list["OrderDetailTable"]] = relationship(back_populates="order")

    __table_args__ = (
        CheckConstraint(
            "order_status IN ('pending','confirmed','delivered','cancelled')",
            name="ck_orders_order_status",
        ),
        CheckConstraint(
            "payment_status IN ('pending','paid','failed')",
            name="ck_orders_payment_status",
        ),
        CheckConstraint(
            "payment_mode IN ('cash','upi','card')",
            name="ck_orders_payment_mode",
        ),
    )


class OrderDetailTable(Base):
    __tablename__ = "order_details"

    order_detail_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[OrderTable] = relationship(back_populates="order_details")
    item: Mapped[ItemTable] = relationship(back_populates="order_details")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_details_quantity_positive"),
        CheckConstraint("price >= 0", name="ck_order_details_price_nonnegative"),
    )
