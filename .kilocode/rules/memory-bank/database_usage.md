# Database Usage Guidelines - SessionLocal

This document outlines the recommended patterns for interacting with the database using `SessionLocal` to ensure proper session management and transaction handling.

## SessionLocal Overview

`SessionLocal` is a SQLAlchemy session factory configured to provide a database session. It is defined in [`app/core/schemas/__init__.py`](app/core/schemas/__init__.py:35). It is designed to be used as a context manager, ensuring that the database session is correctly opened and closed, and transactions are managed safely.

## Standard Usage with `with` Statement

The primary way to use `SessionLocal` is within a `with` statement. This pattern automatically handles the session lifecycle, including committing changes on success and rolling back on exceptions.

### Example: Querying Data

```python
from app.core.schemas import SessionLocal
from app.core.schemas.sandbox_db import SandboxOrders # Example model

def get_open_orders():
    with SessionLocal() as db_session:
        try:
            open_orders = db_session.query(SandboxOrders).filter_by(order_status='open').all()
            return open_orders
        except Exception as e:
            # Log the error, do not re-raise if it's a non-critical read
            print(f"Error fetching open orders: {e}")
            return []
```

### Example: Adding New Records

```python
from app.core.schemas import SessionLocal
from app.core.schemas.sandbox_db import SandboxTrades # Example model
from datetime import datetime
import pytz

def create_new_trade(trade_data):
    with SessionLocal() as db_session:
        try:
            new_trade = SandboxTrades(
                tradeid=trade_data['tradeid'],
                orderid=trade_data['orderid'],
                user_id=trade_data['user_id'],
                symbol=trade_data['symbol'],
                exchange=trade_data['exchange'],
                action=trade_data['action'],
                quantity=trade_data['quantity'],
                price=trade_data['price'],
                product=trade_data['product'],
                strategy=trade_data['strategy'],
                trade_timestamp=datetime.now(pytz.timezone('Asia/Kolkata'))
            )
            db_session.add(new_trade)
            db_session.commit() # Commit the transaction
            db_session.refresh(new_trade) # Refresh to get any database-generated values (e.g., ID)
            return new_trade
        except Exception as e:
            db_session.rollback() # Rollback on error
            print(f"Error creating new trade: {e}")
            raise # Re-raise the exception after rollback
```

### Example: Updating Existing Records

```python
from app.core.schemas import SessionLocal
from app.core.schemas.sandbox_db import SandboxOrders # Example model
from datetime import datetime
import pytz

def update_order_status(order_id, new_status, execution_price=None, filled_quantity=None):
    with SessionLocal() as db_session:
        try:
            order = db_session.query(SandboxOrders).filter_by(orderid=order_id).first()
            if order:
                order.order_status = new_status
                if execution_price is not None:
                    order.average_price = execution_price
                if filled_quantity is not None:
                    order.filled_quantity = filled_quantity
                    order.pending_quantity = order.quantity - filled_quantity
                order.update_timestamp = datetime.now(pytz.timezone('Asia/Kolkata'))
                db_session.commit() # Commit the transaction
                db_session.refresh(order)
                return order
            else:
                print(f"Order with ID {order_id} not found.")
                return None
        except Exception as e:
            db_session.rollback() # Rollback on error
            print(f"Error updating order {order_id}: {e}")
            raise # Re-raise the exception after rollback
```

## Key Principles

-   **Context Manager:** Always use `SessionLocal()` with a `with` statement.
-   **Explicit `commit()`:** Call `db_session.commit()` to persist changes to the database.
-   **Explicit `rollback()`:** In `except` blocks, call `db_session.rollback()` to revert any uncommitted changes if an error occurs.
-   **Error Handling:** Wrap database operations in `try...except` blocks to gracefully handle exceptions and ensure `rollback()` is called.
-   **Refresh Objects:** After committing changes, consider `db_session.refresh(obj)` if you need to access database-generated values or updated states of the object within the same session.

## FastAPI Integration with `get_db` Dependency

For FastAPI routes, `SessionLocal` is typically used as a dependency via the `get_db` function (defined in `app.core.schemas`). This approach ensures that a database session is automatically created for each request and properly closed afterwards, simplifying session management in your API endpoints.

### Example: Using `get_db` in a FastAPI Route

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.schemas import get_db
from app.core.schemas.sandbox_db import SandboxOrders # Example model

router = APIRouter()

@router.get("/orders/{order_id}")
def read_order(order_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a single order by its ID.
    The 'db' session is injected by FastAPI and managed by get_db().
    """
    order = db.query(SandboxOrders).filter_by(orderid=order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/orders/")
def create_order(order_data: dict, db: Session = Depends(get_db)):
    """
    Create a new order.
    The 'db' session is injected by FastAPI and managed by get_db().
    """
    try:
        new_order = SandboxOrders(**order_data)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating order: {e}")
```

### Key Principles for FastAPI Integration

-   **Dependency Injection:** Always use `db: Session = Depends(get_db)` in your FastAPI route functions to inject a database session.
-   **No Manual `with` Statement in Routes:** When using `Depends(get_db)`, you do *not* need to use `with SessionLocal()` directly within your route function, as `get_db` handles the session lifecycle.
-   **`db.commit()` and `db.rollback()`:** Within your route logic, remember to call `db.commit()` to save changes and `db.rollback()` in `except` blocks if an error occurs during a transaction.
-   **Error Handling:** Use FastAPI's `HTTPException` for API-specific error responses when database operations fail.