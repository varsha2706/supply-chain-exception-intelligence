from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SupplyChainQueryRequest(BaseModel):
    query: str
    gemini_api_key: Optional[str] = None

class SupplyChainQueryResponse(BaseModel):
    query: str
    answer: str
    insights: List[Dict[str, Any]] = []
    recommended_actions: List[str] = []
    grounded_data_summary: Optional[Dict[str, Any]] = None

class ExceptionItem(BaseModel):
    exception_id: str
    exception_type: str
    severity: str
    entity_id: str
    entity_type: str
    product_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    supplier_name: Optional[str] = None
    deterministic_metrics: Dict[str, Any]
    explanation: str
    recommended_action: str
    status: str = 'OPEN'
    created_at: Optional[str] = None

class SupplierComparisonItem(BaseModel):
    supplier_id: str
    supplier_name: str
    category: str
    country: str
    total_orders: int
    delivered_orders: int
    delayed_orders: int
    otif_rate_pct: float
    stated_lead_time_days: int
    avg_actual_lead_time_days: float
    lead_time_variance_days: float
    reliability_score: float
    risk_tier: str
    ai_risk_assessment: Optional[str] = None

class ForecastItem(BaseModel):
    product_id: str
    product_name: str
    warehouse_id: str
    warehouse_name: str
    current_stock: float
    reserved_stock: float
    inbound_stock: float
    net_available_stock: float
    daily_demand_rate: float
    days_of_supply: float
    projected_stockout_date: Optional[str] = None
    shortage_units_7d: float
    risk_level: str
    ai_explanation: Optional[str] = None
    ai_recommendation: Optional[str] = None

class DashboardKPIs(BaseModel):
    total_products: int
    total_orders: int
    total_suppliers: int
    total_warehouses: int
    total_inventory_value: float
    out_of_stock_count: int
    safety_stock_breaches: int
    delayed_orders_count: int
    critical_exceptions_count: int
    total_exceptions_count: int
    average_otif_rate: float
