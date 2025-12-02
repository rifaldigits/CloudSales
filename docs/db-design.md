# DB Design Decisions (PostgreSQL)

- Engine: PostgreSQL
- Naming:
  - Tabel: plural snake_case (clients, users, products, ...)
  - Primary key: id (UUID v4) untuk semua tabel utama.
- Timestamps:
  - Semua tabel: created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ).
- JSON:
  - Gunakan tipe jsonb:
    - metadata_json
    - payload_json
    - field lain yang disebut JSON di PDF.

# Relationships

- clients 1:N subscriptions
- clients 1:N quotations
- users (misalnya sales_user_id) 1:N quotations
- quotations 1:N quotation_items
- quotations 1:1 subscriptions (ketika ACCEPTED)
- subscriptions 1:N billing_cycles
- subscriptions 1:N invoices (kalau tabel invoice terpisah, sesuaikan)
- invoices 1:N payments
- wallet_accounts 1:N payments
- webhook_events → refer ke invoice_id/payment_id/other (sesuai PDF)
- provisioning_tasks → refer ke subscription_id/client_id/product_id (sesuai PDF)
