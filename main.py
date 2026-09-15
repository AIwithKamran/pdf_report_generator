from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import sqlite3
import uuid
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from playwright.sync_api import sync_playwright

DATABASE_FILE = "report.db"
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


# --- Database Lifespan (Startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    yield


app = FastAPI(lifespan=lifespan)


# --- Helpers: Data Fetching & HTML Generation ---
def fetch_report_data():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()

        # Overall summary
        cursor.execute("""
            SELECT 
                COUNT(*), 
                COALESCE(ROUND(SUM(amount), 2), 0),
                COALESCE(ROUND(AVG(amount), 2), 0)
            FROM orders
        """)
        total_orders, total_revenue, avg_amount = cursor.fetchone()

        # Top 5 products by revenue
        cursor.execute("""
            SELECT 
                product, 
                COUNT(*), 
                COALESCE(ROUND(SUM(amount), 2), 0)
            FROM orders
            GROUP BY product
            ORDER BY SUM(amount) DESC
            LIMIT 5
        """)
        top_products = cursor.fetchall()

        # All orders (log table)
        cursor.execute("""
            SELECT id, customer, product, amount, created_at
            FROM orders
            ORDER BY created_at DESC
        """)
        all_orders = cursor.fetchall()

    return {
        "date": datetime.now().strftime("%B %d, %Y"),
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_amount": avg_amount,
        "top_products": top_products,
        "all_orders": all_orders,
    }


def build_html_template(data):
    top_5_rows = "".join(
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>${r[2]:,.2f}</td></tr>"
        for r in data["top_products"]
    )
    all_order_rows = "".join(
        f"<tr><td>#{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>${r[3]:,.2f}</td><td>{r[4]}</td></tr>"
        for r in data["all_orders"]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Executive Sales Report</title>
    <style>
        @page {{ size: A4; margin: 20mm; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #333; line-height: 1.4; }}
        .kpi-container {{ display: flex; gap: 20px; margin: 20px 0; }}
        .kpi-card {{ border: 1px solid #ddd; padding: 12px 16px; border-radius: 6px; min-width: 140px; background: #fafafa; }}
        .kpi-label {{ font-size: 11px; text-transform: uppercase; color: #666; font-weight: bold; }}
        .kpi-value {{ font-size: 20px; font-weight: bold; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }}
        th, td {{ padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }}
        th {{ background: #f7f7f7; font-weight: 600; }}
        
        /* Print layout rules */
        thead {{ display: table-header-group; }}
        tr {{ break-inside: avoid; page-break-inside: avoid; }}
    </style>
</head>
<body>
    <h1>Executive Sales Report</h1>
    <p style="color: #666;">Generated on {data['date']}</p>
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{data['total_orders']}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">${data['total_revenue']:,.2f}</div>
        </div>
    </div>
    <h2>Top 5 Products</h2>
    <table>
        <thead><tr><th>Product</th><th>Units Sold</th><th>Revenue</th></tr></thead>
        <tbody>{top_5_rows}</tbody>
    </table>
    <h2>All Orders Log</h2>
    <table>
        <thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead>
        <tbody>{all_order_rows}</tbody>
    </table>
</body>
</html>"""


# --- API Routes ---

@app.get("/health")
def health():
    return {"name": "PDF Generator", "version": "v1.1", "status": "running"}


@app.get("/data-details")
def get_report_data():
    data = fetch_report_data()
    return {
        "summary": {
            "total_orders": data["total_orders"],
            "total_revenue": data["total_revenue"],
            "average_order_value": data["avg_amount"],
        },
        "by_product": [
            {"product": r[0], "orders_count": r[1], "total_revenue": r[2]}
            for r in data["top_products"]
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/reports", status_code=status.HTTP_201_CREATED)
def create_report():
    data = fetch_report_data()
    html_content = build_html_template(data)

    file_id = str(uuid.uuid4())[:8]
    pdf_filename = f"report_{file_id}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

    # Render PDF through Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()

    # Record in SQLite
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reports (path, created_at) VALUES (?, ?)",
            (pdf_path, now)
        )
        report_id = cursor.lastrowid
        conn.commit()

    return {
        "id": report_id,
        "file": f"/reports/{report_id}/file"
    }


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, path, created_at FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": row[0],
        "path": row[1],
        "created_at": row[2],
        "file": f"/reports/{row[0]}/file"
    }


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()

    if not row or not os.path.exists(row[0]):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=row[0],
        media_type="application/pdf",
        filename=os.path.basename(row[0])
    )