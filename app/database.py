import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            business_name TEXT,
            business_type TEXT,
            source TEXT DEFAULT 'website',
            status TEXT DEFAULT 'new',
            priority TEXT DEFAULT 'medium',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            billing_cycle TEXT DEFAULT 'monthly',
            features TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            business_name TEXT,
            business_type TEXT,
            plan_id INTEGER,
            status TEXT DEFAULT 'active',
            lead_id INTEGER,
            monthly_rate REAL DEFAULT 0,
            start_date TEXT,
            notes TEXT DEFAULT '',
            industry_crm TEXT DEFAULT '',
            payment_card_type TEXT DEFAULT '',
            payment_card_last4 TEXT DEFAULT '',
            payment_card_expiry TEXT DEFAULT '',
            billing_address TEXT DEFAULT '',
            contract_status TEXT DEFAULT 'pending',
            contract_date TEXT,
            contract_type TEXT DEFAULT '',
            contract_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            invoice_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            paid_date TEXT,
            description TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
        CREATE INDEX IF NOT EXISTS idx_activities_lead ON activities(lead_id);
        CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
        CREATE INDEX IF NOT EXISTS idx_customers_plan ON customers(plan_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
        CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date);
    """)
    # Migrate existing databases: add new customer columns if missing
    migrate_columns = [
        ("industry_crm", "TEXT DEFAULT ''"),
        ("payment_card_type", "TEXT DEFAULT ''"),
        ("payment_card_last4", "TEXT DEFAULT ''"),
        ("payment_card_expiry", "TEXT DEFAULT ''"),
        ("billing_address", "TEXT DEFAULT ''"),
        ("contract_status", "TEXT DEFAULT 'pending'"),
        ("contract_date", "TEXT"),
        ("contract_type", "TEXT DEFAULT ''"),
        ("contract_url", "TEXT DEFAULT ''"),
    ]
    for col_name, col_type in migrate_columns:
        try:
            await db.execute(f"ALTER TABLE customers ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass  # Column already exists

    await db.commit()
    await db.close()
