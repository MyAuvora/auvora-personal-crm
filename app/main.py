from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import aiosqlite
from datetime import datetime

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
