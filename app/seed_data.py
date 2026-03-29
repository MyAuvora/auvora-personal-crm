"""
Demo seed data for Auvora CRM.
Populates the database with realistic plans, leads, customers, invoices, and activities.
"""

import aiosqlite
from datetime import datetime, timedelta
import random
import os

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")


PLANS = [
    {
        "name": "Starter",
        "price": 49.0,
        "billing_cycle": "monthly",
        "features": '["Up to 100 leads", "Basic CRM", "Email support", "1 user"]',
        "is_active": 1,
    },
    {
        "name": "Growth",
        "price": 99.0,
        "billing_cycle": "monthly",
        "features": '["Up to 500 leads", "Full CRM + Pipeline", "Priority support", "5 users", "AI assistant"]',
        "is_active": 1,
    },
    {
        "name": "Professional",
        "price": 199.0,
        "billing_cycle": "monthly",
        "features": '["Unlimited leads", "Full CRM + Pipeline + POS", "Dedicated support", "Unlimited users", "AI assistant", "Custom branding"]',
        "is_active": 1,
    },
    {
        "name": "Enterprise",
        "price": 499.0,
        "billing_cycle": "monthly",
        "features": '["Everything in Professional", "Multi-location", "API access", "Custom integrations", "SLA guarantee", "Onboarding manager"]',
        "is_active": 1,
    },
]

LEADS = [
    # Hot leads - high priority, various stages
    {
        "name": "Sarah Chen",
        "email": "sarah@ironpulse.com",
        "phone": "(813) 555-0142",
        "business_name": "Iron Pulse Fitness",
        "business_type": "Fitness",
        "source": "website",
        "status": "proposal",
        "priority": "high",
        "notes": "Runs a boutique CrossFit gym in Tampa. Looking for member management + POS. Currently uses MindBody but unhappy with pricing. Has 180 members. Demo scheduled for next week.",
        "days_ago": 3,
    },
    {
        "name": "Marcus Rivera",
        "email": "marcus@eliteacademy.com",
        "phone": "(813) 555-0198",
        "business_name": "Elite Academy",
        "business_type": "Education",
        "source": "referral",
        "status": "qualified",
        "priority": "high",
        "notes": "Tutoring center with 3 locations. Referred by Sarah Chen. Needs multi-location CRM with student tracking. Budget approved, wants to see demo first.",
        "days_ago": 5,
    },
    {
        "name": "Jennifer Walsh",
        "email": "jen@zenflow.com",
        "phone": "(727) 555-0167",
        "business_name": "Zen Flow Yoga",
        "business_type": "Wellness",
        "source": "chatbot",
        "status": "negotiation",
        "priority": "high",
        "notes": "Yoga studio with 2 locations. Very interested in AI assistant and scheduling. Asked about annual pricing. Waiting for contract review from her partner.",
        "days_ago": 7,
    },
    # Warm leads - medium priority
    {
        "name": "David Kim",
        "email": "david@sharpcuts.co",
        "phone": "(813) 555-0234",
        "business_name": "Sharp Cuts Barbershop",
        "business_type": "Beauty",
        "source": "social",
        "status": "contacted",
        "priority": "medium",
        "notes": "3-chair barbershop. Found us on Instagram. Interested in appointment scheduling and POS. Currently tracks everything on paper.",
        "days_ago": 10,
    },
    {
        "name": "Amanda Torres",
        "email": "amanda@flexzone.fit",
        "phone": "(941) 555-0312",
        "business_name": "FlexZone Fitness",
        "business_type": "Fitness",
        "source": "website",
        "status": "contacted",
        "priority": "medium",
        "notes": "Small personal training studio. 50 active clients. Needs client management and billing automation. Currently using spreadsheets.",
        "days_ago": 12,
    },
    {
        "name": "Robert Johnson",
        "email": "rjohnson@brightminds.edu",
        "phone": "(813) 555-0456",
        "business_name": "Bright Minds Learning Center",
        "business_type": "Education",
        "source": "event",
        "status": "qualified",
        "priority": "medium",
        "notes": "Met at Tampa Small Business Expo. After-school tutoring program with 200+ students. Very interested in enrollment tracking and parent communication.",
        "days_ago": 8,
    },
    {
        "name": "Lisa Park",
        "email": "lisa@serenity-spa.com",
        "phone": "(727) 555-0589",
        "business_name": "Serenity Day Spa",
        "business_type": "Beauty",
        "source": "website",
        "status": "new",
        "priority": "medium",
        "notes": "Luxury day spa. Interested in integrated booking + POS + client profiles. Currently using Vagaro but wants more CRM features.",
        "days_ago": 2,
    },
    # Cool leads - various
    {
        "name": "Mike Thompson",
        "email": "mike@greenlawn.co",
        "phone": "(813) 555-0678",
        "business_name": "Green Lawn Pro",
        "business_type": "Auxiliary",
        "source": "cold_outreach",
        "status": "new",
        "priority": "low",
        "notes": "Lawn care company. 15 commercial clients. Interested in customer management and invoicing. Follow up next month.",
        "days_ago": 1,
    },
    {
        "name": "Dr. Rachel Adams",
        "email": "radams@alignchiro.com",
        "phone": "(813) 555-0789",
        "business_name": "Align Chiropractic",
        "business_type": "Wellness",
        "source": "referral",
        "status": "proposal",
        "priority": "high",
        "notes": "Chiropractic clinic with 5 providers. Looking for patient CRM + appointment scheduling + SOAP notes. Currently using Practice Fusion. Ready to switch.",
        "days_ago": 4,
    },
    {
        "name": "Carlos Mendez",
        "email": "carlos@tampaboxing.com",
        "phone": "(813) 555-0890",
        "business_name": "Tampa Boxing Club",
        "business_type": "Fitness",
        "source": "social",
        "status": "contacted",
        "priority": "medium",
        "notes": "Boxing gym with 120 members. Found us through Facebook ad. Interested in member check-ins and billing. Wants to see how other gyms use Auvora.",
        "days_ago": 14,
    },
    # Won deals (converted to customers)
    {
        "name": "Emily Watson",
        "email": "emily@peakperformance.fit",
        "phone": "(813) 555-0123",
        "business_name": "Peak Performance Studio",
        "business_type": "Fitness",
        "source": "website",
        "status": "won",
        "priority": "high",
        "notes": "CONVERTED - Signed up for Professional plan. Boutique HIIT studio with 250 members. Very happy with the AI assistant feature.",
        "days_ago": 30,
    },
    {
        "name": "James Martinez",
        "email": "james@kinderprep.com",
        "phone": "(727) 555-0456",
        "business_name": "KinderPrep Academy",
        "business_type": "Education",
        "source": "referral",
        "status": "won",
        "priority": "high",
        "notes": "CONVERTED - Signed up for Growth plan. Preschool with enrollment management needs. 2 locations.",
        "days_ago": 45,
    },
    {
        "name": "Nicole Brown",
        "email": "nicole@glamstudio.com",
        "phone": "(813) 555-0567",
        "business_name": "Glam Studio",
        "business_type": "Beauty",
        "source": "website",
        "status": "won",
        "priority": "medium",
        "notes": "CONVERTED - Signed up for Starter plan. Hair salon with 4 stylists. Needed simple booking and client tracking.",
        "days_ago": 60,
    },
    {
        "name": "Tom Wilson",
        "email": "tom@fitfactory.com",
        "phone": "(941) 555-0789",
        "business_name": "Fit Factory",
        "business_type": "Fitness",
        "source": "event",
        "status": "won",
        "priority": "high",
        "notes": "CONVERTED - Signed up for Enterprise plan. Large gym chain with 4 locations. Needed multi-location support and API access.",
        "days_ago": 90,
    },
    # Lost deal
    {
        "name": "Kevin Lee",
        "email": "kevin@zenithgym.com",
        "phone": "(813) 555-0345",
        "business_name": "Zenith Gym",
        "business_type": "Fitness",
        "source": "website",
        "status": "lost",
        "priority": "medium",
        "notes": "Lost to competitor (GymDesk). Price was the main factor. May revisit in 6 months when contract expires.",
        "days_ago": 20,
    },
    {
        "name": "Priya Patel",
        "email": "priya@innerpeace.com",
        "phone": "(727) 555-0901",
        "business_name": "Inner Peace Wellness",
        "business_type": "Wellness",
        "source": "chatbot",
        "status": "new",
        "priority": "medium",
        "notes": "Meditation and wellness center. Just launched, looking for CRM options. Very early stage, needs follow-up in 2 weeks.",
        "days_ago": 1,
    },
    {
        "name": "Derek Foster",
        "email": "derek@speedkick.com",
        "phone": "(813) 555-1012",
        "business_name": "SpeedKick Soccer Academy",
        "business_type": "Education",
        "source": "website",
        "status": "new",
        "priority": "low",
        "notes": "Youth soccer academy. 80 enrolled students. Interested in enrollment and parent communication features.",
        "days_ago": 1,
    },
]

CUSTOMERS = [
    {
        "name": "Emily Watson",
        "email": "emily@peakperformance.fit",
        "phone": "(813) 555-0123",
        "business_name": "Peak Performance Studio",
        "business_type": "Fitness",
        "plan_name": "Professional",
        "status": "active",
        "monthly_rate": 199.0,
        "start_date_days_ago": 28,
        "notes": "Flagship fitness customer. Using all features including POS and AI assistant. Very engaged, provides great feedback.",
        "industry_crm": "Fitness",
        "payment_card_type": "Visa",
        "payment_card_last4": "4242",
        "payment_card_expiry": "03/27",
        "billing_address": "1450 W Swann Ave, Tampa, FL 33606",
        "contract_status": "signed",
        "contract_date_days_ago": 28,
        "contract_type": "Annual",
        "contract_url": "",
    },
    {
        "name": "James Martinez",
        "email": "james@kinderprep.com",
        "phone": "(727) 555-0456",
        "business_name": "KinderPrep Academy",
        "business_type": "Education",
        "plan_name": "Growth",
        "status": "active",
        "monthly_rate": 99.0,
        "start_date_days_ago": 42,
        "notes": "Education vertical customer. Using CRM and pipeline features. Expanding to 3rd location next quarter.",
        "industry_crm": "Education",
        "payment_card_type": "Mastercard",
        "payment_card_last4": "8831",
        "payment_card_expiry": "11/26",
        "billing_address": "2200 Central Ave, St. Petersburg, FL 33712",
        "contract_status": "signed",
        "contract_date_days_ago": 42,
        "contract_type": "Annual",
        "contract_url": "",
    },
    {
        "name": "Nicole Brown",
        "email": "nicole@glamstudio.com",
        "phone": "(813) 555-0567",
        "business_name": "Glam Studio",
        "business_type": "Beauty",
        "plan_name": "Starter",
        "status": "active",
        "monthly_rate": 49.0,
        "start_date_days_ago": 56,
        "notes": "Small beauty salon. Steady user, mainly uses client management and booking. Candidate for upsell to Growth plan.",
        "industry_crm": "Beauty",
        "payment_card_type": "Visa",
        "payment_card_last4": "1122",
        "payment_card_expiry": "08/27",
        "billing_address": "4012 S Dale Mabry Hwy, Tampa, FL 33611",
        "contract_status": "signed",
        "contract_date_days_ago": 56,
        "contract_type": "Monthly",
        "contract_url": "",
    },
    {
        "name": "Tom Wilson",
        "email": "tom@fitfactory.com",
        "phone": "(941) 555-0789",
        "business_name": "Fit Factory",
        "business_type": "Fitness",
        "plan_name": "Enterprise",
        "status": "active",
        "monthly_rate": 499.0,
        "start_date_days_ago": 85,
        "notes": "Largest customer. 4-location gym chain. Heavy API user. Has dedicated onboarding manager.",
        "industry_crm": "Fitness",
        "payment_card_type": "Amex",
        "payment_card_last4": "5567",
        "payment_card_expiry": "01/28",
        "billing_address": "7001 N Dale Mabry Hwy, Sarasota, FL 34243",
        "contract_status": "signed",
        "contract_date_days_ago": 85,
        "contract_type": "Annual",
        "contract_url": "",
    },
    {
        "name": "Sandra Hughes",
        "email": "sandra@bodyelite.com",
        "phone": "(813) 555-1234",
        "business_name": "Body Elite Training",
        "business_type": "Fitness",
        "plan_name": "Growth",
        "status": "active",
        "monthly_rate": 99.0,
        "start_date_days_ago": 35,
        "notes": "Personal training studio. 8 trainers, 200 clients. Loves the scheduling feature.",
        "industry_crm": "Fitness",
        "payment_card_type": "Visa",
        "payment_card_last4": "9034",
        "payment_card_expiry": "06/27",
        "billing_address": "3401 W Kennedy Blvd, Tampa, FL 33609",
        "contract_status": "signed",
        "contract_date_days_ago": 35,
        "contract_type": "Annual",
        "contract_url": "",
    },
    {
        "name": "Alex Nguyen",
        "email": "alex@codeninjas-tampa.com",
        "phone": "(813) 555-5678",
        "business_name": "Code Ninjas Tampa",
        "business_type": "Education",
        "plan_name": "Professional",
        "status": "active",
        "monthly_rate": 199.0,
        "start_date_days_ago": 20,
        "notes": "Kids coding school. Using enrollment tracking and parent communication heavily. Wants API access for website integration.",
        "industry_crm": "Education",
        "payment_card_type": "Mastercard",
        "payment_card_last4": "6677",
        "payment_card_expiry": "12/26",
        "billing_address": "14302 N Dale Mabry Hwy, Tampa, FL 33618",
        "contract_status": "signed",
        "contract_date_days_ago": 20,
        "contract_type": "Monthly",
        "contract_url": "",
    },
    {
        "name": "Maria Gonzalez",
        "email": "maria@bellacura.com",
        "phone": "(727) 555-9012",
        "business_name": "Bella Cura Medspa",
        "business_type": "Beauty",
        "plan_name": "Professional",
        "status": "active",
        "monthly_rate": 199.0,
        "start_date_days_ago": 15,
        "notes": "Medical spa. 6 providers, 500+ clients. Using POS heavily for product sales and service packages.",
        "industry_crm": "Beauty",
        "payment_card_type": "Visa",
        "payment_card_last4": "3345",
        "payment_card_expiry": "09/27",
        "billing_address": "150 2nd Ave N, St. Petersburg, FL 33701",
        "contract_status": "signed",
        "contract_date_days_ago": 15,
        "contract_type": "Annual",
        "contract_url": "",
    },
    {
        "name": "Ryan Cooper",
        "email": "ryan@suncoastfit.com",
        "phone": "(941) 555-3456",
        "business_name": "Suncoast Fitness",
        "business_type": "Fitness",
        "plan_name": "Starter",
        "status": "churned",
        "monthly_rate": 49.0,
        "start_date_days_ago": 120,
        "notes": "Churned after 3 months. Said they didn't have time to implement fully. Consider reaching out again with onboarding offer.",
        "industry_crm": "Fitness",
        "payment_card_type": "Visa",
        "payment_card_last4": "7788",
        "payment_card_expiry": "05/26",
        "billing_address": "8200 S Tamiami Trail, Sarasota, FL 34231",
        "contract_status": "expired",
        "contract_date_days_ago": 120,
        "contract_type": "Monthly",
        "contract_url": "",
    },
]


def _gen_activities(lead_status: str, days_ago: int) -> list:
    """Generate realistic activity history based on lead status."""
    activities = []
    base = datetime.utcnow() - timedelta(days=days_ago)

    activities.append({
        "type": "created",
        "description": "Lead created",
        "created_at": base.isoformat(),
    })

    if lead_status in ("contacted", "qualified", "proposal", "negotiation", "won", "lost"):
        activities.append({
            "type": "email",
            "description": "Sent introductory email with product overview and case studies",
            "created_at": (base + timedelta(hours=2)).isoformat(),
        })
        activities.append({
            "type": "call",
            "description": "Initial discovery call. Discussed business needs and current pain points.",
            "created_at": (base + timedelta(days=1)).isoformat(),
        })

    if lead_status in ("qualified", "proposal", "negotiation", "won", "lost"):
        activities.append({
            "type": "note",
            "description": "Qualified as a strong fit. Has budget authority and timeline.",
            "created_at": (base + timedelta(days=2)).isoformat(),
        })
        activities.append({
            "type": "meeting",
            "description": "Live demo session. Showed CRM, pipeline, and AI assistant features.",
            "created_at": (base + timedelta(days=3)).isoformat(),
        })

    if lead_status in ("proposal", "negotiation", "won"):
        activities.append({
            "type": "email",
            "description": "Sent pricing proposal and implementation timeline",
            "created_at": (base + timedelta(days=4)).isoformat(),
        })

    if lead_status in ("negotiation", "won"):
        activities.append({
            "type": "call",
            "description": "Follow-up call to discuss proposal. Negotiating contract terms.",
            "created_at": (base + timedelta(days=5)).isoformat(),
        })

    if lead_status == "won":
        activities.append({
            "type": "note",
            "description": "Deal closed! Customer signed contract and onboarding scheduled.",
            "created_at": (base + timedelta(days=6)).isoformat(),
        })

    if lead_status == "lost":
        activities.append({
            "type": "note",
            "description": "Deal lost. Went with competitor on price. Set reminder to follow up in 6 months.",
            "created_at": (base + timedelta(days=5)).isoformat(),
        })

    return activities


def _gen_invoices(customer: dict, plan_price: float) -> list:
    """Generate invoice history for a customer."""
    invoices = []
    start = datetime.utcnow() - timedelta(days=customer["start_date_days_ago"])
    months = customer["start_date_days_ago"] // 30 + 1

    for i in range(months):
        inv_date = start + timedelta(days=30 * i)
        due_date = inv_date + timedelta(days=15)
        is_paid = inv_date < datetime.utcnow() - timedelta(days=10)
        is_overdue = not is_paid and due_date < datetime.utcnow()

        if customer["status"] == "churned" and i >= 3:
            break

        invoices.append({
            "amount": plan_price,
            "status": "paid" if is_paid else "pending",
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "paid_date": (inv_date + timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d") if is_paid else None,
            "description": f"{customer['plan_name']} plan - {'Monthly' if True else 'Annual'} subscription",
            "notes": "",
        })

    return invoices


async def seed_demo_data():
    """Seed the database with demo data. Clears existing data first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")

        # Clear existing data (order matters due to foreign keys)
        await db.execute("DELETE FROM invoices")
        await db.execute("DELETE FROM activities")
        await db.execute("DELETE FROM customers")
        await db.execute("DELETE FROM plans")
        await db.execute("DELETE FROM leads")
        await db.commit()

        # Seed plans
        plan_ids = {}
        now = datetime.utcnow().isoformat()
        for plan in PLANS:
            cursor = await db.execute(
                "INSERT INTO plans (name, price, billing_cycle, features, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (plan["name"], plan["price"], plan["billing_cycle"], plan["features"], plan["is_active"], now),
            )
            plan_ids[plan["name"]] = cursor.lastrowid

        # Seed leads
        lead_ids = {}
        for lead in LEADS:
            created = (datetime.utcnow() - timedelta(days=lead["days_ago"])).isoformat()
            cursor = await db.execute(
                """INSERT INTO leads (name, email, phone, business_name, business_type, source, status, priority, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lead["name"], lead["email"], lead["phone"], lead["business_name"], lead["business_type"],
                 lead["source"], lead["status"], lead["priority"], lead["notes"], created, created),
            )
            lead_id = cursor.lastrowid
            lead_ids[lead["name"]] = lead_id

            # Add activities
            for act in _gen_activities(lead["status"], lead["days_ago"]):
                await db.execute(
                    "INSERT INTO activities (lead_id, type, description, created_at) VALUES (?, ?, ?, ?)",
                    (lead_id, act["type"], act["description"], act["created_at"]),
                )

        # Seed customers
        for cust in CUSTOMERS:
            plan_id = plan_ids.get(cust["plan_name"])
            lead_id = lead_ids.get(cust["name"])
            start_date = (datetime.utcnow() - timedelta(days=cust["start_date_days_ago"])).strftime("%Y-%m-%d")
            created = (datetime.utcnow() - timedelta(days=cust["start_date_days_ago"])).isoformat()

            contract_date = (datetime.utcnow() - timedelta(days=cust.get("contract_date_days_ago", cust["start_date_days_ago"]))).strftime("%Y-%m-%d") if cust.get("contract_date_days_ago") else None
            cursor = await db.execute(
                """INSERT INTO customers (name, email, phone, business_name, business_type, plan_id, status, lead_id, monthly_rate, start_date, notes,
                   industry_crm, payment_card_type, payment_card_last4, payment_card_expiry, billing_address,
                   contract_status, contract_date, contract_type, contract_url, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cust["name"], cust["email"], cust["phone"], cust["business_name"], cust["business_type"],
                 plan_id, cust["status"], lead_id, cust["monthly_rate"], start_date, cust["notes"],
                 cust.get("industry_crm", ""), cust.get("payment_card_type", ""), cust.get("payment_card_last4", ""),
                 cust.get("payment_card_expiry", ""), cust.get("billing_address", ""),
                 cust.get("contract_status", "pending"), contract_date, cust.get("contract_type", ""),
                 cust.get("contract_url", ""), created, created),
            )
            customer_id = cursor.lastrowid

            # Generate invoices for this customer
            plan_price = cust["monthly_rate"]
            for inv in _gen_invoices(cust, plan_price):
                await db.execute(
                    """INSERT INTO invoices (customer_id, amount, status, invoice_date, due_date, paid_date, description, notes, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (customer_id, inv["amount"], inv["status"], inv["invoice_date"], inv["due_date"],
                     inv["paid_date"], inv["description"], inv["notes"], datetime.utcnow().isoformat()),
                )

        await db.commit()

    return {
        "plans": len(PLANS),
        "leads": len(LEADS),
        "customers": len(CUSTOMERS),
        "message": "Demo data seeded successfully!",
    }
