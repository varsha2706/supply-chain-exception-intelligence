import os
import pandas as pd
from .database import get_connection, init_db

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def load_sample_datasets():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM exceptions_log")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM suppliers")
    cursor.execute("DELETE FROM warehouses")
    conn.commit()

    prod_csv = os.path.join(DATA_DIR, 'sample_products.csv')
    if os.path.exists(prod_csv):
        df = pd.read_csv(prod_csv)
        df.to_sql('products', conn, if_exists='append', index=False)

    sup_csv = os.path.join(DATA_DIR, 'sample_suppliers.csv')
    if os.path.exists(sup_csv):
        df = pd.read_csv(sup_csv)
        df.to_sql('suppliers', conn, if_exists='append', index=False)

    wh_csv = os.path.join(DATA_DIR, 'sample_warehouses.csv')
    if os.path.exists(wh_csv):
        df = pd.read_csv(wh_csv)
        df.to_sql('warehouses', conn, if_exists='append', index=False)

    inv_csv = os.path.join(DATA_DIR, 'sample_inventory.csv')
    if os.path.exists(inv_csv):
        df = pd.read_csv(inv_csv)
        df.to_sql('inventory', conn, if_exists='append', index=False)

    ord_csv = os.path.join(DATA_DIR, 'sample_orders.csv')
    if os.path.exists(ord_csv):
        df = pd.read_csv(ord_csv)
        df.to_sql('orders', conn, if_exists='append', index=False)

    conn.commit()
    conn.close()
    return {"status": "success", "message": "All sample datasets ingested successfully into SQLite"}

if __name__ == '__main__':
    res = load_sample_datasets()
    print(res)
