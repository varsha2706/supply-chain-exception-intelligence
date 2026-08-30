import sqlite3
import os
import pandas as pd
from typing import Optional

DB_PATH = os.environ.get("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), "supply_chain.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_name TEXT NOT NULL,
        category TEXT,
        unit_cost REAL,
        reorder_point REAL,
        safety_stock REAL,
        daily_demand_rate REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id TEXT PRIMARY KEY,
        supplier_name TEXT NOT NULL,
        category TEXT,
        stated_lead_time_days INTEGER,
        country TEXT,
        reliability_rating REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warehouses (
        warehouse_id TEXT PRIMARY KEY,
        warehouse_name TEXT NOT NULL,
        location TEXT,
        capacity_units REAL,
        current_utilization_pct REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id TEXT PRIMARY KEY,
        product_id TEXT,
        warehouse_id TEXT,
        current_stock REAL,
        reserved_stock REAL,
        inbound_stock REAL,
        last_restocked_date TEXT,
        FOREIGN KEY (product_id) REFERENCES products (product_id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        product_id TEXT,
        supplier_id TEXT,
        warehouse_id TEXT,
        order_date TEXT,
        promised_delivery_date TEXT,
        actual_delivery_date TEXT,
        quantity REAL,
        unit_price REAL,
        status TEXT,
        FOREIGN KEY (product_id) REFERENCES products (product_id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exceptions_log (
        exception_id TEXT PRIMARY KEY,
        exception_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        entity_id TEXT,
        entity_type TEXT,
        product_name TEXT,
        warehouse_name TEXT,
        supplier_name TEXT,
        deterministic_metrics TEXT,
        explanation TEXT,
        recommended_action TEXT,
        status TEXT DEFAULT 'OPEN',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
