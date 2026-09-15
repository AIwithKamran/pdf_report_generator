import os
import sqlite3
from datetime import datetime
from playwright.sync_api import sync_playwright

DATABASE_FILE = "report.db"
OUTPUT_DIR = "reports"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "test.pdf")


def fetch_report_data():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()

        # 1. Grand totals
        cursor.execute("""
            SELECT 
                COUNT(*), 
                COALESCE(ROUND(SUM(amount), 2), 0)
            FROM orders
        """)
        total_orders, total_revenue = cursor.fetchone()

        # 2. Top 5 products by revenue
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

        # 3. All orders (long list to trigger multi-page layout)
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
        "top_products": top_products,
        "all_orders": all_orders,
    }


def generate_html(data):
    # Top 5 rows
    top_5_rows = "".join(
        f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>${row[2]:,.2f}</td></tr>"
        for row in data["top_products"]
    )

    # All 200 orders rows
    all_order_rows = "".join(
        f"<tr><td>#{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>${row[3]:,.2f}</td><td>{row[4]}</td></tr>"
        for row in data["all_orders"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sales Report</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            color: #333;
            line-height: 1.4;
            margin: 0;
        }}
        h1 {{
            margin-bottom: 4px;
        }}
        .date {{
            color: #666;
            margin-bottom: 24px;
        }}
        .kpi-container {{
            display: flex;
            gap: 20px;
            margin-bottom: 28px;
        }}
        .kpi-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            min-width: 160px;
            background: #fafafa;
        }}
        .kpi-label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #777;
            font-weight: 600;
        }}
        .kpi-value {{
            font-size: 22px;
            font-weight: bold;
            margin-top: 6px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 28px;
            font-size: 13px;
        }}
        th, td {{
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: 600;
        }}

        /* --- THE CRITICAL PRINT TRAPS SOLVED --- */
        thead {{
            display: table-header-group; /* Ensures header repeats on every printed page */
        }}
        tr {{
            break-inside: avoid;        /* Prevents row splitting across page boundaries */
            page-break-inside: avoid;   /* Legacy fallback */
        }}
    </style>
</head>
<body>
    <h1>Executive Sales Report</h1>
    <div class="date">Report generated on {data['date']}</div>

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
        <thead>
            <tr>
                <th>Product</th>
                <th>Units Sold</th>
                <th>Revenue</th>
            </tr>
        </thead>
        <tbody>
            {top_5_rows}
        </tbody>
    </table>

    <h2>All Orders Log</h2>
    <table>
        <thead>
            <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
            {all_order_rows}
        </tbody>
    </table>
</body>
</html>
"""


def render_pdf():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = fetch_report_data()
    html_content = generate_html(data)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.pdf(
            path=OUTPUT_PATH,
            format="A4",
            print_background=True,
        )
        browser.close()

    print(f"Report successfully generated at: {OUTPUT_PATH}")


if __name__ == "__main__":
    render_pdf()