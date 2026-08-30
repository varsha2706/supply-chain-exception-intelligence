import pandas as pd
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from .database import get_connection

def run_deterministic_analytics() -> Dict[str, Any]:
    """
    Strictly deterministic analytics engine.
    Calculates low stock breaches, delayed orders, lead time variances,
    supplier OTIF ratings, and 7-day stockout projections.
    """
    conn = get_connection()
    
    # Load core tables into DataFrames
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    inventory_df = pd.read_sql_query("""
        SELECT i.*, p.product_name, p.category, p.unit_cost, p.reorder_point, p.safety_stock, p.daily_demand_rate,
               w.warehouse_name, w.location
        FROM inventory i
        LEFT JOIN products p ON i.product_id = p.product_id
        LEFT JOIN warehouses w ON i.warehouse_id = w.warehouse_id
    """, conn)
    
    orders_df = pd.read_sql_query("""
        SELECT o.*, p.product_name, s.supplier_name, s.stated_lead_time_days, w.warehouse_name
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.product_id
        LEFT JOIN suppliers s ON o.supplier_id = s.supplier_id
        LEFT JOIN warehouses w ON o.warehouse_id = w.warehouse_id
    """, conn)
    
    suppliers_df = pd.read_sql_query("SELECT * FROM suppliers", conn)
    warehouses_df = pd.read_sql_query("SELECT * FROM warehouses", conn)
    conn.close()

    exceptions: List[Dict[str, Any]] = []
    
    # 1. Deterministic Low-Stock and Safety Stock Exceptions
    for _, row in inventory_df.iterrows():
        curr_stock = float(row['current_stock'] or 0)
        reorder = float(row['reorder_point'] or 0)
        safety = float(row['safety_stock'] or 0)
        p_name = row['product_name'] or row['product_id']
        w_name = row['warehouse_name'] or row['warehouse_id']
        
        if curr_stock <= 0:
            exceptions.append({
                'exception_id': f"EXC-STK-{row['inventory_id']}",
                'exception_type': 'OUT_OF_STOCK',
                'severity': 'CRITICAL',
                'entity_id': row['product_id'],
                'entity_type': 'PRODUCT_INVENTORY',
                'product_name': p_name,
                'warehouse_name': w_name,
                'supplier_name': 'N/A',
                'deterministic_metrics': {
                    'current_stock': curr_stock,
                    'reorder_point': reorder,
                    'safety_stock': safety,
                    'deficit_units': reorder - curr_stock,
                    'stock_health_pct': 0.0
                }
            })
        elif curr_stock <= safety:
            exceptions.append({
                'exception_id': f"EXC-STK-{row['inventory_id']}",
                'exception_type': 'SAFETY_STOCK_BREACH',
                'severity': 'HIGH',
                'entity_id': row['product_id'],
                'entity_type': 'PRODUCT_INVENTORY',
                'product_name': p_name,
                'warehouse_name': w_name,
                'supplier_name': 'N/A',
                'deterministic_metrics': {
                    'current_stock': curr_stock,
                    'reorder_point': reorder,
                    'safety_stock': safety,
                    'deficit_to_safety': safety - curr_stock,
                    'stock_health_pct': round((curr_stock / max(reorder, 1)) * 100, 1)
                }
            })
        elif curr_stock <= reorder:
            exceptions.append({
                'exception_id': f"EXC-STK-{row['inventory_id']}",
                'exception_type': 'REORDER_POINT_TRIGGERED',
                'severity': 'MEDIUM',
                'entity_id': row['product_id'],
                'entity_type': 'PRODUCT_INVENTORY',
                'product_name': p_name,
                'warehouse_name': w_name,
                'supplier_name': 'N/A',
                'deterministic_metrics': {
                    'current_stock': curr_stock,
                    'reorder_point': reorder,
                    'safety_stock': safety,
                    'suggested_reorder_qty': reorder * 1.5 - curr_stock,
                    'stock_health_pct': round((curr_stock / max(reorder, 1)) * 100, 1)
                }
            })

    # 2. Deterministic Delayed Orders and In-Transit Bottlenecks
    reference_today = datetime(2026, 8, 25) # Standard operational reference timestamp
    
    for _, order in orders_df.iterrows():
        p_date_str = order['promised_delivery_date']
        a_date_str = order['actual_delivery_date']
        o_date_str = order['order_date']
        status = str(order['status']).upper()
        
        if not p_date_str:
            continue
            
        p_date = datetime.strptime(p_date_str, '%Y-%m-%d')
        delay_days = 0
        is_delayed = False
        
        if status == 'DELIVERED' and a_date_str:
            a_date = datetime.strptime(a_date_str, '%Y-%m-%d')
            if a_date > p_date:
                delay_days = (a_date - p_date).days
                is_delayed = True
        elif status in ['IN_TRANSIT', 'PROCESSING', 'PENDING']:
            if reference_today > p_date:
                delay_days = (reference_today - p_date).days
                is_delayed = True
                
        if is_delayed and delay_days > 0:
            order_val = float(order['quantity'] or 0) * float(order['unit_price'] or 0)
            severity = 'CRITICAL' if (delay_days >= 5 or order_val >= 10000) else ('HIGH' if delay_days >= 3 else 'MEDIUM')
            
            exceptions.append({
                'exception_id': f"EXC-ORD-{order['order_id']}",
                'exception_type': 'ORDER_DELIVERY_DELAY',
                'severity': severity,
                'entity_id': order['order_id'],
                'entity_type': 'PURCHASE_ORDER',
                'product_name': order['product_name'],
                'warehouse_name': order['warehouse_name'],
                'supplier_name': order['supplier_name'],
                'deterministic_metrics': {
                    'order_id': order['order_id'],
                    'delay_days': delay_days,
                    'order_value': order_val,
                    'quantity': float(order['quantity']),
                    'status': status,
                    'promised_date': p_date_str,
                    'order_date': o_date_str
                }
            })

    # 3. 7-Day Stockout Risk Forecasting (Deterministic Run-Rate Model)
    forecast_results = calculate_deterministic_7d_forecast(inventory_df, orders_df, reference_today)
    
    for item in forecast_results:
        if item['risk_level'] in ['CRITICAL', 'HIGH']:
            exceptions.append({
                'exception_id': f"EXC-FCST-{item['product_id']}-{item['warehouse_id']}",
                'exception_type': '7DAY_STOCKOUT_PREDICTION',
                'severity': item['risk_level'],
                'entity_id': item['product_id'],
                'entity_type': 'STOCKOUT_FORECAST',
                'product_name': item['product_name'],
                'warehouse_name': item['warehouse_name'],
                'supplier_name': 'Multiple',
                'deterministic_metrics': {
                    'days_of_supply': item['days_of_supply'],
                    'daily_demand_rate': item['daily_demand_rate'],
                    'net_available_stock': item['net_available_stock'],
                    'projected_stockout_date': item['projected_stockout_date'],
                    'shortage_units_7d': item['shortage_units_7d']
                }
            })

    return {
        'exceptions': exceptions,
        'inventory_df': inventory_df,
        'orders_df': orders_df,
        'suppliers_df': suppliers_df,
        'warehouses_df': warehouses_df,
        'forecast': forecast_results
    }

def calculate_deterministic_7d_forecast(inventory_df: pd.DataFrame, orders_df: pd.DataFrame, ref_date: datetime) -> List[Dict[str, Any]]:
    forecasts = []
    
    for _, row in inventory_df.iterrows():
        p_id = row['product_id']
        w_id = row['warehouse_id']
        curr_stock = float(row['current_stock'] or 0)
        reserved = float(row['reserved_stock'] or 0)
        inbound = float(row['inbound_stock'] or 0)
        daily_demand = float(row['daily_demand_rate'] or 1.0)
        
        # Inbound confirmed stock
        net_avail = max(0.0, curr_stock - reserved + inbound)
        days_of_supply = round(net_avail / daily_demand, 1) if daily_demand > 0 else 999.0
        
        stockout_date_str = None
        shortage_units = 0.0
        risk_level = 'LOW'
        
        if days_of_supply < 7.0:
            stockout_days = int(days_of_supply)
            stockout_dt = ref_date + timedelta(days=stockout_days)
            stockout_date_str = stockout_dt.strftime('%Y-%m-%d')
            expected_7d_demand = daily_demand * 7.0
            shortage_units = round(max(0.0, expected_7d_demand - net_avail), 1)
            
            if days_of_supply <= 2.5:
                risk_level = 'CRITICAL'
            else:
                risk_level = 'HIGH'
        elif days_of_supply < 14.0:
            risk_level = 'MODERATE'
            
        forecasts.append({
            'product_id': p_id,
            'product_name': row['product_name'] or p_id,
            'warehouse_id': w_id,
            'warehouse_name': row['warehouse_name'] or w_id,
            'current_stock': curr_stock,
            'reserved_stock': reserved,
            'inbound_stock': inbound,
            'net_available_stock': net_avail,
            'daily_demand_rate': daily_demand,
            'days_of_supply': days_of_supply,
            'projected_stockout_date': stockout_date_str,
            'shortage_units_7d': shortage_units,
            'risk_level': risk_level
        })
        
    forecasts.sort(key=lambda x: x['days_of_supply'])
    return forecasts

def calculate_supplier_comparison() -> List[Dict[str, Any]]:
    """
    Deterministic calculation of Supplier performance metrics:
    OTIF %, Lead Time Drift, Delayed Order Ratio, Reliability Index.
    """
    conn = get_connection()
    suppliers_df = pd.read_sql_query("SELECT * FROM suppliers", conn)
    orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    
    results = []
    
    for _, sup in suppliers_df.iterrows():
        s_id = sup['supplier_id']
        s_orders = orders_df[orders_df['supplier_id'] == s_id]
        
        total_orders = len(s_orders)
        if total_orders == 0:
            continue
            
        stated_lt = int(sup['stated_lead_time_days'] or 10)
        delivered_orders = 0
        delayed_orders = 0
        actual_lead_times = []
        
        for _, ord_row in s_orders.iterrows():
            status = str(ord_row['status']).upper()
            p_date_str = ord_row['promised_delivery_date']
            a_date_str = ord_row['actual_delivery_date']
            o_date_str = ord_row['order_date']
            
            if status == 'DELIVERED':
                delivered_orders += 1
                if a_date_str and p_date_str:
                    a_dt = datetime.strptime(a_date_str, '%Y-%m-%d')
                    p_dt = datetime.strptime(p_date_str, '%Y-%m-%d')
                    if a_dt > p_dt:
                        delayed_orders += 1
                if a_date_str and o_date_str:
                    a_dt = datetime.strptime(a_date_str, '%Y-%m-%d')
                    o_dt = datetime.strptime(o_date_str, '%Y-%m-%d')
                    actual_lead_times.append((a_dt - o_dt).days)
            elif status in ['IN_TRANSIT', 'PROCESSING', 'PENDING']:
                if p_date_str:
                    ref_dt = datetime(2026, 8, 25)
                    p_dt = datetime.strptime(p_date_str, '%Y-%m-%d')
                    if ref_dt > p_dt:
                        delayed_orders += 1

        avg_actual_lt = round(sum(actual_lead_times) / len(actual_lead_times), 1) if actual_lead_times else float(stated_lt)
        lt_variance = round(avg_actual_lt - stated_lt, 1)
        
        on_time_count = max(0, total_orders - delayed_orders)
        otif_pct = round((on_time_count / max(total_orders, 1)) * 100, 1)
        
        # Reliability score = 60% OTIF + 40% Lead time adherence
        lt_score = max(0.0, 100.0 - (max(0.0, lt_variance) * 10.0))
        reliability_score = round((otif_pct * 0.6) + (lt_score * 0.4), 1)
        
        if otif_pct >= 90.0 and lt_variance <= 1.0:
            risk_tier = 'LOW_RISK'
        elif otif_pct >= 75.0:
            risk_tier = 'MODERATE_RISK'
        else:
            risk_tier = 'HIGH_RISK'
            
        results.append({
            'supplier_id': s_id,
            'supplier_name': sup['supplier_name'],
            'category': sup['category'],
            'country': sup['country'],
            'total_orders': total_orders,
            'delivered_orders': delivered_orders,
            'delayed_orders': delayed_orders,
            'otif_rate_pct': otif_pct,
            'stated_lead_time_days': stated_lt,
            'avg_actual_lead_time_days': avg_actual_lt,
            'lead_time_variance_days': lt_variance,
            'reliability_score': reliability_score,
            'risk_tier': risk_tier
        })
        
    results.sort(key=lambda x: x['reliability_score'], reverse=True)
    return results

def get_dashboard_kpis() -> Dict[str, Any]:
    conn = get_connection()
    products_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    suppliers_count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    warehouses_count = conn.execute("SELECT COUNT(*) FROM warehouses").fetchone()[0]
    orders_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    
    inv_df = pd.read_sql_query("""
        SELECT i.current_stock, p.unit_cost, p.safety_stock, p.reorder_point
        FROM inventory i
        LEFT JOIN products p ON i.product_id = p.product_id
    """, conn)
    
    total_val = float((inv_df['current_stock'] * inv_df['unit_cost']).sum()) if not inv_df.empty else 0.0
    out_of_stock = int((inv_df['current_stock'] <= 0).sum()) if not inv_df.empty else 0
    safety_breaches = int(((inv_df['current_stock'] > 0) & (inv_df['current_stock'] <= inv_df['safety_stock'])).sum()) if not inv_df.empty else 0
    
    # Exceptions summary
    exc_count = conn.execute("SELECT COUNT(*) FROM exceptions_log WHERE status='OPEN'").fetchone()[0]
    critical_exc = conn.execute("SELECT COUNT(*) FROM exceptions_log WHERE severity='CRITICAL' AND status='OPEN'").fetchone()[0]
    conn.close()
    
    supplier_bench = calculate_supplier_comparison()
    avg_otif = round(sum(s['otif_rate_pct'] for s in supplier_bench) / len(supplier_bench), 1) if supplier_bench else 0.0
    
    return {
        'total_products': products_count,
        'total_suppliers': suppliers_count,
        'total_warehouses': warehouses_count,
        'total_orders': orders_count,
        'total_inventory_value': round(total_val, 2),
        'out_of_stock_count': out_of_stock,
        'safety_stock_breaches': safety_breaches,
        'delayed_orders_count': sum(s['delayed_orders'] for s in supplier_bench),
        'critical_exceptions_count': critical_exc,
        'total_exceptions_count': exc_count,
        'average_otif_rate': avg_otif
    }
