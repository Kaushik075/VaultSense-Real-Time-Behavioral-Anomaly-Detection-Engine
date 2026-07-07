"""
VaultSense — Fast Data Generation Script
Author: Kaushik Yeddanapudi
Generates 25,000 user activity rows + baselines + injected anomalies
Completes in ~2-3 minutes
"""

import psycopg2
import psycopg2.extras  # for fast batch insert
import random
import uuid
from datetime import datetime, timedelta

# ============================================================
# PASTE YOUR NEON CREDENTIALS HERE
# ============================================================
DB_HOST = "ep-odd-river-at628qvm.c-9.us-east-1.aws.neon.tech"
DB_NAME = "******"
DB_USER = "*****"
DB_PASSWORD = "********"
DB_PORT = xxxx

# ============================================================
# CONNECT
# ============================================================
print("Connecting to Neon DB...")
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require"
    )
    conn.autocommit = False
    cur = conn.cursor()
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit()

# ============================================================
# CLEAR OLD DATA (fresh start)
# ============================================================
print("Clearing old data...")
cur.execute("TRUNCATE TABLE user_activity_log RESTART IDENTITY CASCADE;")
cur.execute("TRUNCATE TABLE user_behavior_baselines RESTART IDENTITY CASCADE;")
cur.execute("TRUNCATE TABLE behavioral_audit_log RESTART IDENTITY CASCADE;")
conn.commit()
print("✅ Tables cleared!")

# ============================================================
# SETUP
# ============================================================
USERS = [f"user_{i:04d}" for i in range(1, 501)]  # 500 users
DEVICES = ["mobile", "desktop", "tablet", "smart_tv"]
COUNTRIES = ["India", "USA", "UK", "Germany", "Singapore", "UAE", "Australia"]
CITIES = {
    "India": ["Hyderabad", "Mumbai", "Delhi", "Bangalore"],
    "USA": ["New York", "LA", "Chicago"],
    "UK": ["London", "Manchester"],
    "Germany": ["Berlin", "Munich"],
    "Singapore": ["Singapore"],
    "UAE": ["Dubai"],
    "Australia": ["Sydney"]
}
EVENT_TYPES = ["stream_start", "stream_pause", "stream_end",
               "login", "logout", "subscription_purchase",
               "password_change", "profile_update", "content_download"]

# ============================================================
# GENERATE USER BASELINES
# ============================================================
print("Generating user baselines...")

user_baselines = {}
baseline_rows = []

for user_id in USERS:
    country = random.choice(COUNTRIES)
    device = random.choice(DEVICES)
    device_id = f"dev_{uuid.uuid4().hex[:12]}"
    avg_events = round(random.uniform(2, 8), 2)
    avg_txn = round(random.uniform(100, 500), 2)

    user_baselines[user_id] = {
        "usual_device_type": device,
        "usual_country": country,
        "avg_transaction_amount": avg_txn,
        "last_known_device_id": device_id
    }

    baseline_rows.append((user_id, device, country, avg_events, avg_txn, "18-23", device_id))

psycopg2.extras.execute_values(cur, """
    INSERT INTO user_behavior_baselines
    (user_id, usual_device_type, usual_country, avg_events_per_hour,
     avg_transaction_amount, typical_active_hours, last_known_device_id)
    VALUES %s ON CONFLICT (user_id) DO NOTHING
""", baseline_rows)
conn.commit()
print(f"✅ {len(USERS)} user baselines inserted!")

# ============================================================
# GENERATE ALL EVENTS IN ONE SHOT
# ============================================================
print("Generating all events...")

all_rows = []

# 20,000 normal events
for _ in range(244700):
    user_id = random.choice(USERS)
    b = user_baselines[user_id]
    country = b["usual_country"]
    event_type = random.choice(EVENT_TYPES)
    txn = round(random.uniform(0, b["avg_transaction_amount"] * 1.5), 2) if event_type == "subscription_purchase" else 0
    created_at = datetime.now() - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))

    all_rows.append((
        user_id, str(uuid.uuid4()), event_type,
        b["usual_device_type"], b["last_known_device_id"],
        f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
        country, random.choice(CITIES.get(country, ["Unknown"])),
        txn, f"content_{random.randint(1000,9999)}",
        random.randint(1, 10), random.randint(8, 23), created_at
    ))

# ANOMALY 1: 3,000 Credential Stuffing — high velocity, new device
for _ in range(3000):
    user_id = random.choice(USERS)
    b = user_baselines[user_id]
    created_at = datetime.now() - timedelta(days=random.randint(0, 30))
    all_rows.append((
        user_id, str(uuid.uuid4()), "login",
        random.choice(DEVICES), f"dev_UNKNOWN_{uuid.uuid4().hex[:8]}",
        f"10.0.{random.randint(1,255)}.{random.randint(1,255)}",
        b["usual_country"], random.choice(CITIES.get(b["usual_country"], ["Unknown"])),
        0, "N/A", random.randint(20, 40), random.randint(2, 5), created_at
    ))

# ANOMALY 2: 1,500 Account Takeover — foreign country + odd hours
ATTACK_COUNTRIES = ["Russia", "North Korea", "Romania", "Brazil"]
for _ in range(1500):
    user_id = random.choice(USERS)
    created_at = datetime.now() - timedelta(days=random.randint(0, 30))
    all_rows.append((
        user_id, str(uuid.uuid4()), "password_change",
        "mobile", f"dev_FOREIGN_{uuid.uuid4().hex[:8]}",
        f"185.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        random.choice(ATTACK_COUNTRIES), "Unknown",
        0, "N/A", random.randint(5, 12), random.randint(2, 4), created_at
    ))

# ANOMALY 3: 800 Suspicious Downloads — burst activity
for _ in range(800):
    user_id = random.choice(USERS)
    b = user_baselines[user_id]
    created_at = datetime.now() - timedelta(days=random.randint(0, 30))
    all_rows.append((
        user_id, str(uuid.uuid4()), "content_download",
        b["usual_device_type"], b["last_known_device_id"],
        f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
        b["usual_country"], random.choice(CITIES.get(b["usual_country"], ["Unknown"])),
        0, f"content_{random.randint(1000,9999)}",
        random.randint(18, 35), random.randint(2, 5), created_at
    ))

# INSERT ALL AT ONCE
print(f"Inserting {len(all_rows)} rows in one batch...")
psycopg2.extras.execute_values(cur, """
    INSERT INTO user_activity_log
    (user_id, session_id, event_type, device_type, device_id,
     ip_address, country, city, transaction_amount, content_id,
     events_last_10_mins, hour_of_day, created_at)
    VALUES %s
""", all_rows, page_size=5000)
conn.commit()

cur.close()
conn.close()

print("\n" + "="*50)
print("🎉 VaultSense data generation COMPLETE!")
print("="*50)
print(f"✅ 500 user baselines")
print(f"✅ 20,000 normal events")
print(f"✅ 3,000 credential stuffing anomalies")
print(f"✅ 1,500 account takeover anomalies")
print(f"✅ 800 suspicious download anomalies")
print(f"✅ TOTAL: {len(all_rows)} rows in user_activity_log")
print("="*50)
print("Next: Go to Neon → Tables and verify row counts!")