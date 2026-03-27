from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import aiosqlite
from datetime import datetime, timedelta
import json
import os

from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# --- Pydantic Models ---

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    source: str = "website"
    status: str = "new"
    priority: str = "medium"
    notes: str = ""


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None


class ActivityCreate(BaseModel):
    type: str
    description: str


class PlanCreate(BaseModel):
    name: str
    price: float
    billing_cycle: str = "monthly"
    features: str = "[]"
    is_active: int = 1


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    billing_cycle: Optional[str] = None
    features: Optional[str] = None
    is_active: Optional[int] = None


class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    plan_id: Optional[int] = None
    status: str = "active"
    lead_id: Optional[int] = None
    monthly_rate: float = 0
    start_date: Optional[str] = None
    notes: str = ""


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    plan_id: Optional[int] = None
    status: Optional[str] = None
    monthly_rate: Optional[float] = None
    notes: Optional[str] = None


class InvoiceCreate(BaseModel):
    customer_id: int
    amount: float
    status: str = "pending"
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    description: str = ""
    notes: str = ""


class InvoiceUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[str] = None
    paid_date: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class ConvertLeadRequest(BaseModel):
    plan_id: Optional[int] = None
    monthly_rate: float = 0
    notes: str = ""


# --- Helper ---

def row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


# --- Health ---

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# --- Dashboard Stats ---

@app.get("/api/stats")
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    stats = {}

    cursor = await db.execute("SELECT COUNT(*) as total FROM leads")
    row = await cursor.fetchone()
    stats["total_leads"] = row[0]

    cursor = await db.execute(
        "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
    )
    rows = await cursor.fetchall()
    stats["by_status"] = {r[0]: r[1] for r in rows}

    cursor = await db.execute(
        "SELECT priority, COUNT(*) as count FROM leads GROUP BY priority"
    )
    rows = await cursor.fetchall()
    stats["by_priority"] = {r[0]: r[1] for r in rows}

    cursor = await db.execute(
        "SELECT source, COUNT(*) as count FROM leads GROUP BY source"
    )
    rows = await cursor.fetchall()
    stats["by_source"] = {r[0]: r[1] for r in rows}

    cursor = await db.execute(
        "SELECT business_type, COUNT(*) as count FROM leads WHERE business_type IS NOT NULL AND business_type != '' GROUP BY business_type"
    )
    rows = await cursor.fetchall()
    stats["by_business_type"] = {r[0]: r[1] for r in rows}

    cursor = await db.execute(
        "SELECT COUNT(*) FROM leads WHERE created_at >= date('now', '-7 days')"
    )
    row = await cursor.fetchone()
    stats["new_this_week"] = row[0]

    cursor = await db.execute(
        "SELECT COUNT(*) FROM leads WHERE created_at >= date('now', '-30 days')"
    )
    row = await cursor.fetchone()
    stats["new_this_month"] = row[0]

    return stats


# --- Leads CRUD ---

@app.get("/api/leads")
async def list_leads(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
    business_type: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM leads WHERE 1=1"
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if source:
        query += " AND source = ?"
        params.append(source)
    if business_type:
        query += " AND business_type = ?"
        params.append(business_type)
    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR business_name LIKE ? OR phone LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    allowed_sort = ["created_at", "updated_at", "name", "status", "priority"]
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"
    query += f" ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    leads = [row_to_dict(r) for r in rows]

    count_query = "SELECT COUNT(*) FROM leads WHERE 1=1"
    count_params: list = []
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    if priority:
        count_query += " AND priority = ?"
        count_params.append(priority)
    if source:
        count_query += " AND source = ?"
        count_params.append(source)
    if business_type:
        count_query += " AND business_type = ?"
        count_params.append(business_type)
    if search:
        count_query += " AND (name LIKE ? OR email LIKE ? OR business_name LIKE ? OR phone LIKE ?)"
        s = f"%{search}%"
        count_params.extend([s, s, s, s])

    cursor = await db.execute(count_query, count_params)
    total_row = await cursor.fetchone()
    total = total_row[0] if total_row else 0

    return {"leads": leads, "total": total}


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = row_to_dict(row)

    cursor = await db.execute(
        "SELECT * FROM activities WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,),
    )
    activity_rows = await cursor.fetchall()
    lead["activities"] = [row_to_dict(a) for a in activity_rows]

    return lead


@app.post("/api/leads", status_code=201)
async def create_lead(lead: LeadCreate, db: aiosqlite.Connection = Depends(get_db)):
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        """INSERT INTO leads (name, email, phone, business_name, business_type, source, status, priority, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            lead.name,
            lead.email,
            lead.phone,
            lead.business_name,
            lead.business_type,
            lead.source,
            lead.status,
            lead.priority,
            lead.notes,
            now,
            now,
        ),
    )
    await db.commit()
    lead_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO activities (lead_id, type, description) VALUES (?, ?, ?)",
        (lead_id, "created", f"Lead created from {lead.source}"),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.put("/api/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    update: LeadUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    existing_dict = row_to_dict(existing)
    changes = []
    fields_to_update = {}

    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None and str(existing_dict.get(field)) != str(value):
            changes.append(f"{field}: {existing_dict.get(field)} -> {value}")
            fields_to_update[field] = value

    if not fields_to_update:
        return existing_dict

    fields_to_update["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields_to_update)
    values = list(fields_to_update.values()) + [lead_id]
    await db.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)
    await db.commit()

    if changes:
        await db.execute(
            "INSERT INTO activities (lead_id, type, description) VALUES (?, ?, ?)",
            (lead_id, "updated", "; ".join(changes)),
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    await db.commit()
    return {"deleted": True}


# --- Activities ---

@app.post("/api/leads/{lead_id}/activities", status_code=201)
async def add_activity(
    lead_id: int,
    activity: ActivityCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT id FROM leads WHERE id = ?", (lead_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Lead not found")

    cursor = await db.execute(
        "INSERT INTO activities (lead_id, type, description) VALUES (?, ?, ?)",
        (lead_id, activity.type, activity.description),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM activities WHERE id = ?", (cursor.lastrowid,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.get("/api/leads/{lead_id}/activities")
async def list_activities(
    lead_id: int, db: aiosqlite.Connection = Depends(get_db)
):
    cursor = await db.execute("SELECT id FROM leads WHERE id = ?", (lead_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Lead not found")

    cursor = await db.execute(
        "SELECT * FROM activities WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,),
    )
    rows = await cursor.fetchall()
    return [row_to_dict(r) for r in rows]


# --- Plans CRUD ---

@app.get("/api/plans")
async def list_plans(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM plans ORDER BY price ASC")
    rows = await cursor.fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/plans", status_code=201)
async def create_plan(plan: PlanCreate, db: aiosqlite.Connection = Depends(get_db)):
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO plans (name, price, billing_cycle, features, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (plan.name, plan.price, plan.billing_cycle, plan.features, plan.is_active, now),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM plans WHERE id = ?", (cursor.lastrowid,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.put("/api/plans/{plan_id}")
async def update_plan(plan_id: int, update: PlanUpdate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")

    fields_to_update = {}
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            fields_to_update[field] = value

    if not fields_to_update:
        return row_to_dict(existing)

    set_clause = ", ".join(f"{k} = ?" for k in fields_to_update)
    values = list(fields_to_update.values()) + [plan_id]
    await db.execute(f"UPDATE plans SET {set_clause} WHERE id = ?", values)
    await db.commit()

    cursor = await db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


# --- Customers CRUD ---

@app.get("/api/customers")
async def list_customers(
    status: Optional[str] = None,
    plan_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT c.*, p.name as plan_name FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE 1=1"
    params: list = []

    if status:
        query += " AND c.status = ?"
        params.append(status)
    if plan_id:
        query += " AND c.plan_id = ?"
        params.append(plan_id)
    if search:
        query += " AND (c.name LIKE ? OR c.email LIKE ? OR c.business_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    allowed_sort = ["created_at", "updated_at", "name", "status", "monthly_rate"]
    col = sort_by if sort_by in allowed_sort else "created_at"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"
    query += f" ORDER BY c.{col} {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    customers = [row_to_dict(r) for r in rows]

    count_query = "SELECT COUNT(*) FROM customers WHERE 1=1"
    count_params: list = []
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    if plan_id:
        count_query += " AND plan_id = ?"
        count_params.append(plan_id)
    if search:
        count_query += " AND (name LIKE ? OR email LIKE ? OR business_name LIKE ?)"
        s = f"%{search}%"
        count_params.extend([s, s, s])

    cursor = await db.execute(count_query, count_params)
    total_row = await cursor.fetchone()
    total = total_row[0] if total_row else 0

    return {"customers": customers, "total": total}


@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        "SELECT c.*, p.name as plan_name, p.price as plan_price, p.billing_cycle as plan_billing_cycle FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE c.id = ?",
        (customer_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = row_to_dict(row)

    # Get invoices
    cursor = await db.execute(
        "SELECT * FROM invoices WHERE customer_id = ? ORDER BY invoice_date DESC",
        (customer_id,),
    )
    invoice_rows = await cursor.fetchall()
    customer["invoices"] = [row_to_dict(i) for i in invoice_rows]

    return customer


@app.post("/api/customers", status_code=201)
async def create_customer(customer: CustomerCreate, db: aiosqlite.Connection = Depends(get_db)):
    now = datetime.utcnow().isoformat()
    start = customer.start_date or now[:10]
    cursor = await db.execute(
        """INSERT INTO customers (name, email, phone, business_name, business_type, plan_id, status, lead_id, monthly_rate, start_date, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (customer.name, customer.email, customer.phone, customer.business_name, customer.business_type,
         customer.plan_id, customer.status, customer.lead_id, customer.monthly_rate, start, customer.notes, now, now),
    )
    await db.commit()
    customer_id = cursor.lastrowid

    cursor = await db.execute("SELECT c.*, p.name as plan_name FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE c.id = ?", (customer_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: int, update: CustomerUpdate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")

    fields_to_update = {}
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            fields_to_update[field] = value

    if not fields_to_update:
        return row_to_dict(existing)

    fields_to_update["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields_to_update)
    values = list(fields_to_update.values()) + [customer_id]
    await db.execute(f"UPDATE customers SET {set_clause} WHERE id = ?", values)
    await db.commit()

    cursor = await db.execute("SELECT c.*, p.name as plan_name FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE c.id = ?", (customer_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    await db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    await db.commit()
    return {"deleted": True}


# --- Convert Lead to Customer ---

@app.post("/api/customers/convert/{lead_id}", status_code=201)
async def convert_lead_to_customer(
    lead_id: int,
    req: ConvertLeadRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    lead = await cursor.fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Prevent duplicate conversion
    cursor = await db.execute("SELECT id FROM customers WHERE lead_id = ?", (lead_id,))
    if await cursor.fetchone():
        raise HTTPException(status_code=409, detail="Lead has already been converted to a customer")

    lead_dict = row_to_dict(lead)
    now = datetime.utcnow().isoformat()
    today = now[:10]

    # Determine monthly rate from plan or request
    monthly_rate = req.monthly_rate
    if req.plan_id and monthly_rate == 0:
        cursor = await db.execute("SELECT price FROM plans WHERE id = ?", (req.plan_id,))
        plan_row = await cursor.fetchone()
        if plan_row:
            monthly_rate = plan_row[0]

    # Create customer from lead
    cursor = await db.execute(
        """INSERT INTO customers (name, email, phone, business_name, business_type, plan_id, status, lead_id, monthly_rate, start_date, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lead_dict["name"], lead_dict["email"], lead_dict["phone"], lead_dict["business_name"],
         lead_dict["business_type"], req.plan_id, "active", lead_id, monthly_rate, today, req.notes, now, now),
    )
    await db.commit()
    customer_id = cursor.lastrowid

    # Update lead status to won
    await db.execute("UPDATE leads SET status = 'won', updated_at = ? WHERE id = ?", (now, lead_id))
    await db.commit()

    # Log activity on the lead
    await db.execute(
        "INSERT INTO activities (lead_id, type, description) VALUES (?, ?, ?)",
        (lead_id, "converted", f"Converted to customer #{customer_id}"),
    )
    await db.commit()

    # Create first invoice
    due_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    await db.execute(
        """INSERT INTO invoices (customer_id, amount, status, invoice_date, due_date, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (customer_id, monthly_rate, "pending", today, due_date, "First month subscription", now),
    )
    await db.commit()

    cursor = await db.execute("SELECT c.*, p.name as plan_name FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE c.id = ?", (customer_id,))
    row = await cursor.fetchone()
    return row_to_dict(row)


# --- Invoices CRUD ---

@app.get("/api/invoices")
async def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    sort_by: str = "invoice_date",
    sort_order: str = "desc",
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT i.*, c.name as customer_name, c.business_name as customer_business FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id WHERE 1=1"
    params: list = []

    if status:
        query += " AND i.status = ?"
        params.append(status)
    if customer_id:
        query += " AND i.customer_id = ?"
        params.append(customer_id)

    allowed_sort = ["invoice_date", "due_date", "amount", "status", "created_at"]
    col = sort_by if sort_by in allowed_sort else "invoice_date"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"
    query += f" ORDER BY i.{col} {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    invoices = [row_to_dict(r) for r in rows]

    count_query = "SELECT COUNT(*) FROM invoices WHERE 1=1"
    count_params: list = []
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    if customer_id:
        count_query += " AND customer_id = ?"
        count_params.append(customer_id)

    cursor = await db.execute(count_query, count_params)
    total_row = await cursor.fetchone()
    total = total_row[0] if total_row else 0

    return {"invoices": invoices, "total": total}


@app.get("/api/invoices/{invoice_id}")
async def get_invoice(invoice_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        "SELECT i.*, c.name as customer_name, c.business_name as customer_business FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id WHERE i.id = ?",
        (invoice_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return row_to_dict(row)


@app.post("/api/invoices", status_code=201)
async def create_invoice(invoice: InvoiceCreate, db: aiosqlite.Connection = Depends(get_db)):
    # Verify customer exists
    cursor = await db.execute("SELECT id FROM customers WHERE id = ?", (invoice.customer_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.utcnow().isoformat()
    today = now[:10]
    inv_date = invoice.invoice_date or today
    due = invoice.due_date or (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    cursor = await db.execute(
        """INSERT INTO invoices (customer_id, amount, status, invoice_date, due_date, description, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (invoice.customer_id, invoice.amount, invoice.status, inv_date, due, invoice.description, invoice.notes, now),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT i.*, c.name as customer_name, c.business_name as customer_business FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id WHERE i.id = ?",
        (cursor.lastrowid,),
    )
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.put("/api/invoices/{invoice_id}")
async def update_invoice(invoice_id: int, update: InvoiceUpdate, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")

    fields_to_update = {}
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            fields_to_update[field] = value

    # Auto-set paid_date when marking as paid
    if fields_to_update.get("status") == "paid" and "paid_date" not in fields_to_update:
        fields_to_update["paid_date"] = datetime.utcnow().strftime("%Y-%m-%d")

    if not fields_to_update:
        return row_to_dict(existing)

    set_clause = ", ".join(f"{k} = ?" for k in fields_to_update)
    values = list(fields_to_update.values()) + [invoice_id]
    await db.execute(f"UPDATE invoices SET {set_clause} WHERE id = ?", values)
    await db.commit()

    cursor = await db.execute(
        "SELECT i.*, c.name as customer_name, c.business_name as customer_business FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id WHERE i.id = ?",
        (invoice_id,),
    )
    row = await cursor.fetchone()
    return row_to_dict(row)


@app.get("/api/customers/{customer_id}/invoices")
async def list_customer_invoices(customer_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Customer not found")

    cursor = await db.execute(
        "SELECT * FROM invoices WHERE customer_id = ? ORDER BY invoice_date DESC",
        (customer_id,),
    )
    rows = await cursor.fetchall()
    return [row_to_dict(r) for r in rows]


# --- Revenue Stats ---

@app.get("/api/revenue")
async def get_revenue_stats(db: aiosqlite.Connection = Depends(get_db)):
    stats = {}

    # Active customers and MRR
    cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(monthly_rate), 0) FROM customers WHERE status = 'active'")
    row = await cursor.fetchone()
    stats["active_customers"] = row[0]
    stats["mrr"] = round(row[1], 2)
    stats["arr"] = round(row[1] * 12, 2)

    # Total customers by status
    cursor = await db.execute("SELECT status, COUNT(*) FROM customers GROUP BY status")
    rows = await cursor.fetchall()
    stats["by_status"] = {r[0]: r[1] for r in rows}

    # Total customers
    cursor = await db.execute("SELECT COUNT(*) FROM customers")
    row = await cursor.fetchone()
    stats["total_customers"] = row[0]

    # Churn rate (churned / total)
    churned = stats["by_status"].get("churned", 0)
    stats["churn_rate"] = round((churned / stats["total_customers"] * 100) if stats["total_customers"] > 0 else 0, 1)

    # Revenue collected (paid invoices)
    cursor = await db.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'paid'")
    row = await cursor.fetchone()
    stats["total_collected"] = round(row[0], 2)

    # Pending revenue
    cursor = await db.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'pending'")
    row = await cursor.fetchone()
    stats["pending_revenue"] = round(row[0], 2)

    # Overdue invoices
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'pending' AND due_date < ?", (today,))
    row = await cursor.fetchone()
    stats["overdue_count"] = row[0]
    stats["overdue_amount"] = round(row[1], 2)

    # Recent payments (last 5)
    cursor = await db.execute(
        "SELECT i.*, c.name as customer_name, c.business_name as customer_business FROM invoices i LEFT JOIN customers c ON i.customer_id = c.id WHERE i.status = 'paid' ORDER BY i.paid_date DESC LIMIT 5"
    )
    rows = await cursor.fetchall()
    stats["recent_payments"] = [row_to_dict(r) for r in rows]

    # Monthly revenue trend (last 6 months)
    trend = []
    now = datetime.utcnow()
    for i in range(5, -1, -1):
        # Calculate month offset with proper calendar arithmetic
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = f"{year:04d}-{month:02d}-01"
        # Next month boundary
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        month_end = f"{next_year:04d}-{next_month:02d}-01"
        month_label = datetime(year, month, 1).strftime("%b")
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'paid' AND paid_date >= ? AND paid_date < ?",
            (month_start, month_end),
        )
        row = await cursor.fetchone()
        trend.append({"month": month_label, "revenue": round(row[0], 2)})
    stats["revenue_trend"] = trend

    # Customers by plan
    cursor = await db.execute(
        "SELECT COALESCE(p.name, 'No Plan'), COUNT(*) FROM customers c LEFT JOIN plans p ON c.plan_id = p.id WHERE c.status = 'active' GROUP BY p.name"
    )
    rows = await cursor.fetchall()
    stats["by_plan"] = {r[0]: r[1] for r in rows}

    return stats


# --- Serve React Frontend ---

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Try to serve the exact file first
        file_path = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fall back to index.html for SPA routing
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
