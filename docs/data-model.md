# Database Design – Subscription Platform

Dokumen ini menjelaskan desain **tabel** untuk setiap entitas di platform subscription,
berdasarkan spesifikasi “Desain Data & Workflow Platform Subscription (Tanpa Diagram)”.

## 1. Konvensi Umum

**Keputusan teknis (global):**

- **RDBMS**: PostgreSQL (mis. Cloud SQL di GCP).
- **Primary key standar**  
  - Kolom: `id`  
  - Tipe: `uuid`  
  - Default: `gen_random_uuid()`  
  - Alasan: lebih gampang digenerate dari backend / worker, aman untuk sharding, dan tidak bocorin urutan data.
- **Timestamps standar** untuk semua tabel:
  - `created_at timestamptz` (NOT NULL, default `now()`)  
  - `updated_at timestamptz` (NOT NULL, default `now()`, di-update via trigger / aplikasi)
- **Kolom uang**:
  - Pakai `numeric(18,2)` untuk `amount`, `total_amount`, `subtotal_amount`, `balance`, dll.  
  - Alasan: akurat untuk uang, tidak ada floating point error.
- **Kolom kurs**:
  - `numeric(18,6)` untuk `exchange_rate`.
- **Kolom JSON**:
  - Pakai `jsonb` (`metadata_json`, `config_json`, `payload_json`, `attachments_meta_json`, `raw_payload_json`).
- **Enum / status / type**:
  - Di level desain ini ditulis sebagai `text` dengan daftar nilai yang diperbolehkan.
  - Implementasi bisa:
    - Postgres enum type, atau
    - `text` + `CHECK` constraint.
- **Index default**:
  - PK selalu punya index.
  - Semua kolom FK harus di-index (mis. `client_id`, `subscription_id`, `billing_cycle_id`, dll).
  - Kolom yang sering dipakai filter / lookup diberi `INDEX` (mis. `email`, `status`, `workspace_domain`, `xendit_*_id`).

---

## 2. Tabel per Entitas

### 2.1. `clients`

**Tujuan**  
Menyimpan data perusahaan pelanggan, termasuk yang masih prospek (LEAD), dan memisahkan kontak billing vs kontak sales. :contentReference[oaicite:1]{index=1}  

**Kolom spesifik (di luar `id`, `created_at`, `updated_at`):**

- `name varchar(255) NOT NULL`  
  Nama perusahaan (nama dagang).
- `legal_name varchar(255)`  
  Nama hukum jika berbeda dari `name`.
- `billing_email varchar(255) NOT NULL`  
  Email utama untuk invoice & faktur.
- `contact_email varchar(255)`  
  Email kontak Sales (bisa sama dengan `billing_email`).
- `phone varchar(50)`  
  Nomor telepon.
- `billing_address text`  
  Alamat billing.
- `tax_number varchar(100)`  
  NPWP atau nomor pajak lain.
- `tax_card_file_url text`  
  URL/path file scan kartu NPWP yang disimpan di storage.
- `status text NOT NULL`  
  - Nilai yang diperbolehkan: `LEAD`, `ACTIVE`, `SUSPENDED`, `CHURNED`.
- `workspace_domain varchar(255)`  
  Domain Google Workspace, mis. `example.com`.
- `has_portal_account boolean NOT NULL DEFAULT false`  
  Menjadi `true` setelah pembayaran pertama sukses & akun portal dibuat.
- `google_customer_id varchar(255)`  
  Identifier client di ekosistem Google (opsional).

**Index / constraint tambahan:**

- `UNIQUE (billing_email)` (opsional tapi direkomendasikan).
- `UNIQUE (workspace_domain)` (kalau domain harus unik).
- `UNIQUE (google_customer_id)` (kalau digunakan).

**Relasi utama:**

- 1 `client` → banyak `users` (role CLIENT).  
- 1 `client` → banyak `quotations`.  
- 1 `client` → banyak `subscriptions`.  
- 1 `client` → banyak `payments`.  
- 1 `client` → 1 `wallet_accounts`.

---

### 2.2. `users`

**Tujuan**  
Menyimpan akun pengguna yang bisa login (Sales, Admin, Finance, Client). :contentReference[oaicite:2]{index=2}  

**Kolom spesifik:**

- `email varchar(255) NOT NULL`  
  Email login (unik).
- `password_hash text NOT NULL`  
  Hash password (mis. bcrypt/argon2, bukan plaintext).
- `full_name varchar(255) NOT NULL`  
  Nama lengkap.
- `role text NOT NULL`  
  Nilai yang diperbolehkan: `CLIENT`, `SALES`, `ADMIN`, `FINANCE`.
- `client_id uuid NULL`  
  FK ke `clients(id)` – hanya diisi jika `role = 'CLIENT'`.
- `is_active boolean NOT NULL DEFAULT true`  
  Status akun (boleh login atau tidak).

**Index / constraint tambahan:**

- `UNIQUE (email)`.
- `INDEX (client_id)`.

**Relasi utama:**

- Banyak `users` (role CLIENT) → 1 `client`.  
- `users` (role SALES) dihubungkan ke `quotations.sales_user_id`.  
- `users.id` bisa direferensikan oleh `email_logs.user_id`.

---

### 2.3. `products`

**Tujuan**  
Semua produk yang bisa masuk quotation & subscription: Google Workspace, GCP, domain, managed service fee, addon, dll. :contentReference[oaicite:3]{index=3}  

**Kolom spesifik:**

- `code varchar(100) NOT NULL`  
  Kode produk internal (mis. `GW_BUS_STD`, `GCP_VM`, `DOMAIN_ID`).
- `name varchar(255) NOT NULL`  
  Nama produk.
- `type text NOT NULL`  
  Nilai contoh: `GWORKSPACE`, `GCP`, `DOMAIN`, `ADDON`, `SERVICE`.
- `description text`  
  Deskripsi produk.
- `default_billing_period text`  
  Mis. `MONTHLY`, `YEARLY`.
- `is_active boolean NOT NULL DEFAULT true`  
  Apakah produk masih dijual.
- `google_sku varchar(255)`  
  SKU resmi Google (jika ada).
- `metadata_json jsonb`  
  Konfigurasi tambahan (region GCP, jenis VM, dll).

**Index / constraint:**

- `UNIQUE (code)`.
- `INDEX (type)`.

---

### 2.4. `quotations`

**Tujuan**  
Menyimpan penawaran harga yang disusun Sales dan keterkaitannya dengan Cosmic. :contentReference[oaicite:4]{index=4}  

**Catatan desain:**  
Di dokumen ada penamaan yang typo untuk “total dalam mata uang client”. Di sini **diputuskan** pakai nama kolom `total_amount_client` untuk kejelasan.

**Kolom spesifik:**

- `client_id uuid NOT NULL`  
  FK ke `clients(id)`.
- `sales_user_id uuid NOT NULL`  
  FK ke `users(id)` (role SALES).
- `number varchar(100) NOT NULL`  
  Nomor quotation internal (bisa dibuat unik per tahun).
- `status text NOT NULL`  
  Nilai: `DRAFT`, `SENT`, `ACCEPTED`, `REJECTED`, `EXPIRED`.
- `total_amount numeric(18,2) NOT NULL`  
  Total nilai quotation dalam mata uang internal (mis. USD).
- `currency text NOT NULL DEFAULT 'USD'`  
  Mata uang internal.
- `client_currency text NOT NULL DEFAULT 'IDR'`  
  Mata uang yang tampil ke client.
- `exchange_rate numeric(18,6) NOT NULL`  
  Kurs USD → client_currency saat quotation dibuat.
- `total_amount_client numeric(18,2) NOT NULL`  
  Total dalam client_currency (IDR) yang ditampilkan di PDF.
- `valid_until date`  
  Tanggal berakhir masa berlaku quotation.
- `related_subscription_id uuid NULL`  
  FK ke `subscriptions(id)` ketika sudah diwujudkan menjadi subscription.
- `cosmic_id varchar(255)`  
  ID quotation di sistem Cosmic.
- `pdf_url text`  
  URL PDF quotation dari Cosmic.
- `gmail_thread_id varchar(255)`  
  ID thread Gmail (opsional).

**Index / constraint:**

- `UNIQUE (number)` (disarankan).
- `INDEX (client_id)`, `INDEX (sales_user_id)`, `INDEX (status)`.

---

### 2.5. `quotation_items`

**Tujuan**  
Menyimpan line item di quotation (seat Workspace, VM GCP, domain, managed fee, dll). :contentReference[oaicite:5]{index=5}  

**Kolom spesifik:**

- `quotation_id uuid NOT NULL`  
  FK ke `quotations(id)`.
- `product_id uuid NULL`  
  FK ke `products(id)` – boleh `NULL` jika item custom.
- `description text`  
  Deskripsi baris (opsional kalau mau lebih spesifik).
- `quantity integer NOT NULL`  
  Jumlah unit (seat, VM, domain, dsb).
- `unit_price numeric(18,2) NOT NULL`  
  Harga per unit (mata uang internal, default USD).
- `unit_price_client numeric(18,2) NOT NULL`  
  Harga per unit dalam client_currency (IDR), hasil dari `unit_price * exchange_rate`.
- `discount_percent numeric(5,2) DEFAULT 0`  
  Diskon % jika ada.
- `subtotal_amount numeric(18,2) NOT NULL`  
  Nilai setelah diskon (mata uang internal).
- `subtotal_amount_client numeric(18,2) NOT NULL`  
  Nilai setelah diskon dalam client_currency.

**Index / relasi:**

- `INDEX (quotation_id)`.
- `INDEX (product_id)`.

---

### 2.6. `subscriptions`

**Tujuan**  
Menyimpan kontrak langganan jangka panjang (aktif, pending, suspended, dll). :contentReference[oaicite:6]{index=6}  

**Kolom spesifik:**

- `client_id uuid NOT NULL`  
  FK ke `clients(id)`.
- `created_by_user_id uuid NOT NULL`  
  FK ke `users(id)` (Sales/Admin yang membuat).
- `status text NOT NULL`  
  Nilai: `PENDING_ACTIVATION`, `ACTIVE`, `SUSPENDED`, `CANCELLED`, `EXPIRED`.
- `billing_period text NOT NULL`  
  Nilai: `MONTHLY`, `YEARLY`.
- `start_date date`  
  Tanggal mulai (setelah pembayaran pertama sukses).
- `end_date date`  
  Tanggal selesai (opsional; bisa null untuk ongoing).
- `next_billing_date date`  
  Tanggal penagihan berikutnya.
- `payment_method_type text NOT NULL`  
  Nilai: `XENDIT_SUBSCRIPTION`, `MANUAL`, `WALLET`.
- `is_manual boolean NOT NULL DEFAULT false`  
  True jika subscription dibuat manual (ketika Xendit down).
- `xendit_subscription_id varchar(255)`  
  ID subscription di Xendit (jika pakai fitur mereka).
- `currency text NOT NULL`  
  Mata uang untuk subscription ini.
- `notes text`  
  Catatan tambahan.

**Index / relasi:**

- `INDEX (client_id)`.
- `INDEX (status)`.
- `INDEX (next_billing_date)`.

---

### 2.7. `subscription_items`

**Tujuan**  
Menyimpan detail isi subscription: produk apa saja, quantity, nilai, dan status provisioning. :contentReference[oaicite:7]{index=7}  

**Kolom spesifik:**

- `subscription_id uuid NOT NULL`  
  FK ke `subscriptions(id)`.
- `product_id uuid NOT NULL`  
  FK ke `products(id)`.
- `description text`  
  Deskripsi baris.
- `quantity integer NOT NULL`  
  Jumlah seat / resource.
- `unit_price numeric(18,2) NOT NULL`  
  Harga per unit (bisa copy dari quotation atau disesuaikan).
- `amount numeric(18,2) NOT NULL`  
  Total per baris.
- `provisioning_status text NOT NULL`  
  Nilai: `PENDING`, `ACTIVE`, `SUSPENDED`, `TERMINATED`.
- `google_workspace_subscription_id varchar(255)`  
  ID subscription/resource di Workspace (jika applicable).
- `gcp_resource_id varchar(255)`  
  ID resource di GCP (project / VM ID).
- `config_json jsonb`  
  Konfigurasi tambahan (tipe VM, region, dll).

**Index / relasi:**

- `INDEX (subscription_id)`.
- `INDEX (product_id)`.
- `INDEX (provisioning_status)`.

---

### 2.8. `billing_cycles`

**Tujuan**  
Menyimpan tiap periode penagihan (initial & recurring) dan menjadi penghubung quotation → invoice Finance → pembayaran Xendit. :contentReference[oaicite:8]{index=8}  

**Kolom spesifik:**

- `subscription_id uuid NOT NULL`  
  FK ke `subscriptions(id)`.
- `period_start date NOT NULL`  
  Awal periode yang ditagihkan.
- `period_end date NOT NULL`  
  Akhir periode tagihan.
- `due_date date`  
  Tanggal jatuh tempo invoice.
- `amount numeric(18,2) NOT NULL`  
  Jumlah tagihan final (client currency, biasanya IDR, sudah termasuk pajak).
- `currency text NOT NULL DEFAULT 'IDR'`  
  Mata uang invoice Finance.
- `status text NOT NULL`  
  Nilai: `PENDING`, `INVOICE_REQUESTED`, `INVOICED`, `PAID`, `FAILED`, `CANCELLED`.
- `is_initial_cycle boolean NOT NULL DEFAULT false`  
  True untuk tagihan pertama.
- `quoted_amount numeric(18,2)`  
  Nilai hasil perhitungan platform (sebelum finalisasi Finance).
- `invoice_number_external varchar(100)`  
  Nomor invoice versi sistem Finance.
- `invoice_file_url text`  
  URL file invoice (PDF).
- `tax_invoice_file_url text`  
  URL file faktur pajak (PDF).
- `xendit_invoice_id varchar(255)`  
  ID invoice di Xendit (jika ada).
- `last_reminder_sent_at timestamptz`  
  Timestamp reminder terakhir ke client.

**Index / relasi:**

- `INDEX (subscription_id)`.
- `INDEX (status)`.
- `INDEX (due_date)`.

---

### 2.9. `payments`

**Tujuan**  
Mencatat pembayaran aktual via Xendit maupun manual. :contentReference[oaicite:9]{index=9}  

**Kolom spesifik:**

- `client_id uuid NOT NULL`  
  FK ke `clients(id)`.
- `subscription_id uuid`  
  FK ke `subscriptions(id)` (boleh null jika terkait hal lain).
- `billing_cycle_id uuid`  
  FK ke `billing_cycles(id)` untuk mengikat ke periode tertentu.
- `amount numeric(18,2) NOT NULL`  
  Jumlah yang dibayar.
- `currency text NOT NULL`  
  Mata uang.
- `status text NOT NULL`  
  Nilai: `PENDING`, `SUCCESS`, `FAILED`, `REFUNDED`.
- `method text NOT NULL`  
  Nilai: `XENDIT_EWALLET`, `XENDIT_CC`, `XENDIT_VA`, `MANUAL`, dll.
- `xendit_payment_id varchar(255)`  
  ID payment di Xendit.
- `xendit_subscription_id varchar(255)`  
  ID subscription Xendit (untuk recurring).
- `paid_at timestamptz`  
  Waktu pembayaran berhasil.
- `failure_reason text`  
  Alasan jika `status = FAILED`.

**Index / relasi:**

- `INDEX (client_id)`.
- `INDEX (subscription_id)`.
- `INDEX (billing_cycle_id)`.
- `INDEX (status)`.

---

### 2.10. `wallet_accounts`

**Tujuan**  
Akun wallet/deposit per client (opsional fitur). :contentReference[oaicite:10]{index=10}  

**Kolom spesifik:**

- `client_id uuid NOT NULL`  
  FK ke `clients(id)` – satu-satunya wallet per client.
- `balance numeric(18,2) NOT NULL DEFAULT 0`  
  Saldo saat ini.
- `currency text NOT NULL`  
  Mata uang saldo (mis. IDR).

**Index / constraint:**

- `UNIQUE (client_id)` (one-to-one dengan `clients`).

---

### 2.11. `wallet_transactions`

**Tujuan**  
Log semua perubahan saldo wallet (topup, charge, refund, adjustment). :contentReference[oaicite:11]{index=11}  

**Kolom spesifik:**

- `wallet_account_id uuid NOT NULL`  
  FK ke `wallet_accounts(id)`.
- `type text NOT NULL`  
  Nilai: `TOPUP`, `CHARGE`, `REFUND`, `ADJUSTMENT`.
- `direction text NOT NULL`  
  Nilai: `IN`, `OUT`.
- `amount numeric(18,2) NOT NULL`  
  Besar perubahan saldo.
- `related_type text`  
  Mis. `PAYMENT`, `SUBSCRIPTION`, `MANUAL`.
- `related_id uuid`  
  ID entitas terkait (payment/subscription/dll).
- `created_at timestamptz NOT NULL DEFAULT now()`  
  (Untuk tabel ini, `created_at` adalah timestamp event transaksi; `updated_at` umumnya jarang dipakai, bisa tetap ada global.)

**Index / relasi:**

- `INDEX (wallet_account_id)`.
- `INDEX (related_type, related_id)`.

---

### 2.12. `email_logs`

**Tujuan**  
Menyimpan semua email penting (quotation, request invoice, email ke client, reminder, dll). :contentReference[oaicite:12]{index=12}  

**Kolom spesifik:**

- `direction text NOT NULL`  
  Nilai: `OUTBOUND`, `INBOUND`.
- `related_type text`  
  Mis. `QUOTATION`, `INVOICE_REQUEST`, `CLIENT_MAIL`, `REMINDER`, `PAYMENT_STATUS`, dll.
- `related_id uuid`  
  ID entitas terkait (quotation_id, billing_cycle_id, dll).
- `user_id uuid`  
  FK ke `users(id)` (Sales/Admin/Finance/Client) – boleh null jika purely sistem.
- `from_email varchar(255) NOT NULL`  
  Alamat pengirim.
- `to_email varchar(255) NOT NULL`  
  Alamat tujuan.
- `subject varchar(255) NOT NULL`  
  Subjek email.
- `ai_model varchar(100)`  
  Nama model AI (mis. `gemini-1.5-pro`).
- `ai_prompt text`  
  Prompt yang dipakai untuk generate teks.
- `ai_generated_body text`  
  Draft body dari AI.
- `final_body text`  
  Body final yang dikirim / disimpan.
- `status text NOT NULL`  
  Nilai: `DRAFT`, `SENT`, `FAILED`, `RECEIVED`, `PARSED`.
- `gmail_message_id varchar(255)`  
  ID message di Gmail.
- `has_attachments boolean NOT NULL DEFAULT false`  
- `attachments_meta_json jsonb`  
  Metadata lampiran (nama file invoice/faktur, dll).
- `sent_at timestamptz`  
  Waktu email terkirim (kalau `status = SENT`).

**Index / relasi:**

- `INDEX (related_type, related_id)`.
- `INDEX (user_id)`.
- `INDEX (status)`.

---

### 2.13. `provisioning_tasks`

**Tujuan**  
Unit kerja otomatisasi untuk mengaktifkan/menonaktifkan layanan di Workspace/GCP. :contentReference[oaicite:13]{index=13}  

**Kolom spesifik:**

- `subscription_item_id uuid NOT NULL`  
  FK ke `subscription_items(id)`.
- `action text NOT NULL`  
  Nilai: `ACTIVATE`, `SUSPEND`, `CHANGE_QUANTITY`, `TERMINATE`.
- `target_system text NOT NULL`  
  Nilai: `GWORKSPACE`, `GCP`.
- `payload_json jsonb NOT NULL`  
  Data yang dibutuhkan (domain, user list, project ID, dll).
- `status text NOT NULL`  
  Nilai: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`.
- `external_reference varchar(255)`  
  ID job/task di sistem eksternal (jika ada).
- `error_message text`  
  Pesan error jika gagal.
- `executed_at timestamptz`  
  Waktu task dieksekusi.

**Index / relasi:**

- `INDEX (subscription_item_id)`.
- `INDEX (status)`.

---

### 2.14. `webhook_events`

**Tujuan**  
Log webhook dari Xendit (payment success, failed, subscription charge). :contentReference[oaicite:14]{index=14}  

**Kolom spesifik:**

- `source text NOT NULL`  
  Mis. `XENDIT`.
- `event_type text NOT NULL`  
  Mis. `PAYMENT_SUCCEEDED`, `PAYMENT_FAILED`, `SUBSCRIPTION_CHARGED`.
- `raw_payload_json jsonb NOT NULL`  
  Payload lengkap dari Xendit (untuk audit/debug).
- `xendit_subscription_id varchar(255)`  
  ID subscription Xendit (jika ada).
- `xendit_invoice_id varchar(255)`  
  ID invoice di Xendit (jika ada).
- `processed boolean NOT NULL DEFAULT false`  
  Apakah event sudah diproses oleh workflow internal.
- `processed_at timestamptz`  
  Waktu pemrosesan.
- `created_at timestamptz NOT NULL DEFAULT now()`  
  Waktu event diterima.

**Index / relasi:**

- `INDEX (event_type)`.
- `INDEX (xendit_subscription_id)`.
- `INDEX (xendit_invoice_id)`.
- `INDEX (processed)`.

---

## 3. Ringkasan Relasi Utama

- `clients` ↔ `users` (1:N, khusus role CLIENT).  
- `clients` ↔ `quotations` (1:N).  
- `clients` ↔ `subscriptions` (1:N).  
- `clients` ↔ `payments` (1:N).  
- `clients` ↔ `wallet_accounts` (1:1).  

- `users (SALES)` ↔ `quotations` via `sales_user_id`.  
- `users` ↔ `email_logs` via `user_id`.  

- `products` ↔ `quotation_items` (1:N).  
- `products` ↔ `subscription_items` (1:N).  

- `quotations` ↔ `quotation_items` (1:N).  
- `quotations` ↔ `subscriptions` (opsional 1:1) via `related_subscription_id`.  

- `subscriptions` ↔ `subscription_items` (1:N).  
- `subscriptions` ↔ `billing_cycles` (1:N).  
- `subscriptions` ↔ `payments` (1:N).  

- `billing_cycles` ↔ `payments` (1:N).  
- `billing_cycles` ↔ `email_logs` (1:N) via `related_type/related_id`.  

- `wallet_accounts` ↔ `wallet_transactions` (1:N).  

- `subscription_items` ↔ `provisioning_tasks` (1:N).  

- `webhook_events` ↔ `payments` (1:N atau N:1 tergantung logika; event bisa generate/update payment).

