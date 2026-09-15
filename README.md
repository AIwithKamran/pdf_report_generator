## Architectural & Engineering Highlights

### 1. Print CSS Strategy (Clean Page Breaks)
Converting dynamic web layouts into physical or PDF pages introduces the classic table row slicing bug, where a single record is bisected horizontally across a page break. This project solves that at the document layer:
* **`tr { break-inside: avoid; page-break-inside: avoid; }`**: Enforces atomic table rows. If a row cannot fit on the remaining space of a page, the browser cleanly shunts the entire row to the top of the next page.
* **`thead { display: table-header-group; }`**: Guarantees column headers repeat automatically at the top of every subsequent printed page, preserving scannability across multi-page datasets.

### 2. Idempotency Under Rapid Retries
Double-clicking a report generation button causes thread starvation and CPU spikes if unhandled.
* **Mechanism**: Every incoming `POST /reports` query checks whether a report for the current UTC day has already been created and verified on disk.
* **Behavior**: An existing daily report immediately returns `200 OK` with the existing ID and file path. Passing `{"force": true}` bypasses the check to trigger a fresh build returning `201 Created`.
* **Business Impact**: This check protects against server compute and memory starvation caused by duplicate, expensive browser renders. In transactional environments, lacking idempotency can lead to double-charging a customer or executing duplicate deliveries—costing real revenue, payment dispute fees, and customer trust.

### 3. Asynchronous Background Queuing Threshold
Currently, the PDF pipeline renders synchronously inside the request lifecycle, keeping the connection open for 1–3 seconds.
> **Production Threshold:** Move generation to an asynchronous background queue (such as Celery, ARQ, or Redis Queue) as soon as p95 request latency exceeds **2 seconds**, concurrent users exceed worker thread pools, or dataset volumes cause memory pressure that risks request timeouts.

---

## Project Structure

```text
.
├── main.py              # FastAPI app, endpoints, and PDF generation pipeline
├── seed.py              # Database initialization and mock order generator
├── report.db            # SQLite database (orders + reports tables)
├── reports/             # Output directory storing rendered PDF documents
├── requirements.txt     # Python runtime dependencies
└── README.md            # Technical documentation
