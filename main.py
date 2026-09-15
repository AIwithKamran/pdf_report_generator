from datetime import datetime, timezone
import sqlite3
from fastapi import FastAPI

DATABASE_FILE = "report.db"
app = FastAPI()


@app.get("/health")
def health():
    return {"name": "PDF Generator", "version": "v1.1", "status": "running"}


@app.get("/data-details")
def get_report_data():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()

        # 1. Overall totals across all orders
        cursor.execute("""
            SELECT 
                COUNT(*), 
                COALESCE(ROUND(SUM(amount), 2), 0), 
                COALESCE(ROUND(AVG(amount), 2), 0)
            FROM orders
        """)
        total_count, grand_total, overall_avg = cursor.fetchone()

        # 2. Breakdown aggregated by product
        cursor.execute("""
            SELECT 
                product,
                COUNT(*), 
                COALESCE(ROUND(SUM(amount), 2), 0), 
                COALESCE(ROUND(AVG(amount), 2), 0) 
            FROM orders
            GROUP BY product
        """)
        rows = cursor.fetchall()

    product_summary = [
        {
            "product": row[0],
            "orders_count": row[1],
            "total_revenue": row[2],
            "average_order_value": row[3],
        }
        for row in rows
    ]

    return {
        "summary": {
            "total_orders": total_count,
            "total_revenue": grand_total,
            "average_order_value": overall_avg,
        },
        "by_product": product_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }