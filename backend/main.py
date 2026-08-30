import os
import json
import io
import pandas as pd
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .database import init_db, get_connection
from .models import (
    SupplyChainQueryRequest,
    SupplyChainQueryResponse,
    ExceptionItem,
    SupplierComparisonItem,
    ForecastItem,
    DashboardKPIs
)
from .analytics_engine import (
    run_deterministic_analytics,
    calculate_supplier_comparison,
    get_dashboard_kpis,
    calculate_deterministic_7d_forecast
)
from .ai_service import (
    generate_exception_ai_insights,
    answer_natural_language_query
)
from .sample_data_loader import load_sample_datasets

app = FastAPI(
    title="Supply Chain Exception Intelligence Assistant",
    description="Analytics + GenAI operational intelligence platform for enterprise supply chains.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    load_sample_datasets()
    execute_analytics_pipeline()

def execute_analytics_pipeline(gemini_api_key: Optional[str] = None):
    results = run_deterministic_analytics()
    raw_exceptions = results['exceptions']
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exceptions_log")
    
    for exc in raw_exceptions:
        explanation, recommendation = generate_exception_ai_insights(exc, gemini_api_key)
        cursor.execute("""
            INSERT INTO exceptions_log (
                exception_id, exception_type, severity, entity_id, entity_type,
                product_name, warehouse_name, supplier_name, deterministic_metrics,
                explanation, recommended_action, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exc['exception_id'],
            exc['exception_type'],
            exc['severity'],
            exc['entity_id'],
            exc['entity_type'],
            exc.get('product_name'),
            exc.get('warehouse_name'),
            exc.get('supplier_name'),
            json.dumps(exc['deterministic_metrics']),
            explanation,
            recommendation,
            'OPEN'
        ))
    conn.commit()
    conn.close()

# ----------------- REST API Endpoints ----------------- #

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Supply Chain Exception Intelligence Assistant", "version": "1.0.0"}

@app.post("/data/upload")
async def upload_dataset(
    file: Optional[UploadFile] = File(None),
    data_type: Optional[str] = Form("orders")
):
    if not file:
        raise HTTPException(status_code=400, detail="No CSV file provided")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        valid_tables = ["orders", "inventory", "products", "suppliers", "warehouses"]
        target_table = data_type.lower().strip()
        if target_table not in valid_tables:
            raise HTTPException(status_code=400, detail=f"Invalid data_type. Must be one of: {valid_tables}")
            
        conn = get_connection()
        df.to_sql(target_table, conn, if_exists="replace", index=False)
        conn.close()
        
        execute_analytics_pipeline()
        
        return {
            "status": "success",
            "message": f"Successfully ingested {len(df)} records into '{target_table}'. Analytics pipeline re-evaluated.",
            "records_count": len(df),
            "columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV upload failed: {str(e)}")

@app.post("/data/sample")
def reload_sample_data():
    res = load_sample_datasets()
    execute_analytics_pipeline()
    return res

@app.post("/analytics/run")
def trigger_analytics_run(x_gemini_api_key: Optional[str] = Header(None)):
    execute_analytics_pipeline(gemini_api_key=x_gemini_api_key)
    conn = get_connection()
    total_exc = conn.execute("SELECT COUNT(*) FROM exceptions_log WHERE status='OPEN'").fetchone()[0]
    crit_exc = conn.execute("SELECT COUNT(*) FROM exceptions_log WHERE severity='CRITICAL' AND status='OPEN'").fetchone()[0]
    conn.close()
    
    return {
        "status": "success",
        "message": "Deterministic analytics and GenAI explanation pipeline completed successfully.",
        "open_exceptions": total_exc,
        "critical_exceptions": crit_exc
    }

@app.get("/exceptions")
def get_exceptions_queue(
    severity: Optional[str] = Query(None),
    exception_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    conn = get_connection()
    query = "SELECT * FROM exceptions_log WHERE status='OPEN'"
    params = []
    
    if severity and severity != "ALL":
        query += " AND severity = ?"
        params.append(severity.upper())
        
    if exception_type and exception_type != "ALL":
        query += " AND exception_type = ?"
        params.append(exception_type.upper())
        
    if search:
        query += " AND (product_name LIKE ? OR warehouse_name LIKE ? OR supplier_name LIKE ? OR entity_id LIKE ?)"
        s_param = f"%{search}%"
        params.extend([s_param, s_param, s_param, s_param])
        
    query += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, created_at DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "exception_id": r["exception_id"],
            "exception_type": r["exception_type"],
            "severity": r["severity"],
            "entity_id": r["entity_id"],
            "entity_type": r["entity_type"],
            "product_name": r["product_name"],
            "warehouse_name": r["warehouse_name"],
            "supplier_name": r["supplier_name"],
            "deterministic_metrics": json.loads(r["deterministic_metrics"]) if r["deterministic_metrics"] else {},
            "explanation": r["explanation"],
            "recommended_action": r["recommended_action"],
            "status": r["status"],
            "created_at": r["created_at"]
        })
        
    return results

@app.post("/supply/query", response_model=SupplyChainQueryResponse)
def handle_supply_chain_nl_query(payload: SupplyChainQueryRequest):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")
        
    res = answer_natural_language_query(payload.query, payload.gemini_api_key)
    return res

@app.get("/suppliers/compare")
def get_supplier_benchmarks():
    benchmarks = calculate_supplier_comparison()
    return benchmarks

@app.get("/inventory/dashboard", response_model=DashboardKPIs)
def get_inventory_dashboard_data():
    kpis = get_dashboard_kpis()
    return kpis

@app.get("/analytics/forecast")
def get_7day_stockout_forecast():
    conn = get_connection()
    inventory_df = pd.read_sql_query("""
        SELECT i.*, p.product_name, p.category, p.unit_cost, p.reorder_point, p.safety_stock, p.daily_demand_rate,
               w.warehouse_name, w.location
        FROM inventory i
        LEFT JOIN products p ON i.product_id = p.product_id
        LEFT JOIN warehouses w ON i.warehouse_id = w.warehouse_id
    """, conn)
    orders_df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    
    from datetime import datetime
    forecasts = calculate_deterministic_7d_forecast(inventory_df, orders_df, datetime(2026, 8, 25))
    return forecasts

# ----------------- Frontend Static Files ----------------- #
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Supply Chain Exception Intelligence API is running. Access /docs for API documentation."}
