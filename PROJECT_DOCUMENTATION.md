# Biz-Light Project Documentation

## 1. Project Overview

Biz-Light is a Django-based business co-manager for micro-businesses. It combines inventory management, finance tracking, automated alerts, KPI dashboards, AI-generated summaries, and external store synchronization into one user-scoped system.

The codebase is organized as a modular monolith:

- `accounts` handles authentication, onboarding, and business profile setup.
- `inventory` manages products and stock updates.
- `finance` records sales, expenses, and webhook-based sales ingestion.
- `automation` stores alerts and lets users resolve them.
- `dashboard` calculates KPIs, generates reports, renders the main dashboard, and manages store integration.
- `ai_layer` generates natural-language business insights and chat responses.

The project uses Django, Djongo, MongoDB, and a service-oriented pattern inside each app. Business logic is concentrated in service classes and helper functions rather than spread across templates.

## 2. Architecture Summary

### Core data flow

1. A user signs up and completes business onboarding.
2. Products are added in inventory.
3. Sales and expenses are logged in finance.
4. KPI snapshots are recalculated from the latest business data.
5. Alerts are created or resolved automatically based on rules.
6. The dashboard combines KPIs, alerts, inventory, and store data into a single view.
7. AI services turn the latest business state into a readable summary or chat response.

### Design methodology

- User-scoped tenancy: nearly every business object is tied to `request.user`.
- Service layer separation: calculations and AI generation live in services instead of templates.
- Event-driven refresh: inventory and finance updates immediately recalculate KPIs.
- Rule-based automation: alerts are generated from thresholds and business conditions.
- Platform adapters: store synchronization normalizes different e-commerce platforms into one internal format.

## 3. App Map

### `accounts`

Purpose: authentication and onboarding.

Key routes:

- `/` landing page
- `/signup/`
- `/login/`
- `/logout/`
- `/onboarding/`
- `/profile/`

### `inventory`

Purpose: product catalog and stock control.

Key routes:

- `/inventory/`
- `/inventory/add/`
- `/inventory/update-stock/<id>/`

### `finance`

Purpose: sales, expenses, and webhook ingestion.

Key routes:

- `/finance/`
- `/finance/log-sale/`
- `/finance/log-expense/`
- `/finance/api/webhook/sale/`

### `automation`

Purpose: alert center and resolution workflow.

Key routes:

- `/automation/alerts/`
- `/automation/alerts/resolve/<id>/`

### `dashboard`

Purpose: KPI engine, dashboard, reports, PDF export, and store integration.

Key routes:

- `/dashboard/`
- `/dashboard/reports/`
- `/dashboard/export-pdf/`
- `/dashboard/sync-store/`
- `/dashboard/integration/`

### `ai_layer`

Purpose: AI summary generation and chat API.

Key routes:

- `/ai/chat/`

## 4. Models

### `accounts.models.BusinessProfile`

Fields:

- `user`: one-to-one link to Django `User`
- `business_name`
- `business_type`
- `location`
- `description`
- `created_at`

Purpose:

- Stores the business identity used during onboarding and profile display.
- Supports revisiting onboarding to update business details.

### `inventory.models.Product`

Fields:

- `user`
- `name`
- `category`
- `sku`
- `price`
- `cost`
- `stock_level`
- `reorder_point`
- `created_at`
- `updated_at`

Purpose:

- Central product master record.
- Used by finance, dashboard analytics, alerts, and store sync.

### `finance.models.Transaction`

Fields:

- `user`
- `product`
- `type` with values `SALE` and `RESTOCK`
- `quantity`
- `total_amount`
- `timestamp`

Purpose:

- Stores sales and restock movements.
- Used as the main source for revenue and sales metrics.

### `finance.models.Expense`

Fields:

- `user`
- `category`
- `amount`
- `description`
- `date`
- `created_at`

Purpose:

- Stores business expenses used in expense ratio and profit calculations.

### `automation.models.Alert`

Fields:

- `user`
- `type`
- `message`
- `severity`
- `timestamp`
- `is_resolved`

Purpose:

- Represents operational warnings and recommendations.
- Supports manual resolution in the alert center.

### `automation.models.ThresholdConfig`

Fields:

- `user`
- `key`
- `value`
- `description`

Purpose:

- Stores configurable rule thresholds used by the analytics rule engine.

### `dashboard.models.KPISnapshot`

Fields:

- `user`
- `rgr`: revenue growth rate
- `itr`: inventory turnover ratio
- `er`: expense ratio
- `scp`: stock coverage period
- `bhs`: business health score
- `total_revenue`
- `total_expenses`
- `net_profit`
- `report_type`
- `ai_summary`
- `timestamp`

Computed helpers:

- `rgr_percentage`
- `er_percentage`

Purpose:

- Stores the computed business state for a given reporting period.
- Powers dashboard charts, reports, PDF export, and AI summaries.

### `dashboard.models.StoreIntegration`

Fields:

- `user`
- `store_name`
- `platform_type`
- `store_url`
- `api_key`
- `created_at`
- `last_synced`

Purpose:

- Stores external store connection settings for platform sync.

### `ai_layer.models`

- No custom models are defined in this app.

## 5. Key View Methods and Workflows

### `accounts.views`

- `landing(request)`: redirects authenticated users to the dashboard, otherwise renders the landing page.
- `signup_view(request)`: creates a new user through `ExtendedSignUpForm`, logs the user in, and sends them to onboarding.
- `login_view(request)`: authenticates existing users and redirects to the dashboard.
- `onboarding_view(request)`: creates or updates the user’s `BusinessProfile`.
- `profile_view(request)`: displays the current business profile.
- `logout_view(request)`: logs the user out and returns them to the landing page.

### `inventory.views`

- `list_products(request)`: shows the user’s products.
- `add_product(request)`: creates a product, checks SKU uniqueness, optionally creates a low-stock alert, and recalculates KPIs.
- `update_stock(request, pk)`: updates stock quantity, resolves or creates low-stock alerts, and recalculates KPIs.

Helper methods:

- `_create_low_stock_alert(user, product)`: creates a low-stock alert if stock is at or below the reorder point.
- `_resolve_alerts_for_product(user, product)`: marks unresolved low-stock alerts as resolved when stock becomes healthy.

### `finance.views`

- `transaction_list(request)`: shows recent transactions and expenses, plus totals for the selected period.
- `log_sale(request)`: creates a sale transaction, decrements product stock, generates low-stock alerts when needed, and recalculates KPIs.
- `log_expense(request)`: creates an expense and recalculates KPIs.
- `webhook_sale(request)`: accepts JSON webhook payloads, maps SKU to a product, creates a sale, updates stock, and recalculates KPIs.

### `automation.views`

- `alert_list(request)`: displays all alerts for the current user.
- `resolve_alert(request, pk)`: marks a selected alert as resolved.

### `dashboard.views`

- `index(request)`: main dashboard. It loads the latest KPI snapshot, refreshes KPIs when needed, generates AI summaries, collects recent snapshots, recent alerts, inventory products, and monthly/daily chart data.
- `reports_list(request)`: lists historical KPI snapshots and can trigger report generation via `?generate=true`.
- `export_pdf(request)`: creates a PDF report from the latest snapshot and AI summary.
- `integration_settings(request)`: stores store connection settings and redirects to sync.
- `sync_store_data(request)`: pulls orders from the configured platform, normalizes them into transactions, updates stock, updates sync timestamps, and recalculates KPIs.

### `ai_layer.views`

- `chat_api(request)`: builds a rich business context from products, sales, finance totals, KPI snapshots, and recent transactions, then sends it to the AI service.

## 6. Analytics Methodology

The main KPI logic lives in `dashboard.services.AnalyticsService`.

### `calculate_kpis(user, force_new=False, period='daily')`

This method calculates the core business metrics for a user and stores them in `KPISnapshot`.

Metrics:

- Revenue Growth Rate (`rgr`): compares current sales to the previous period.
- Inventory Turnover Ratio (`itr`): compares cost of goods sold against average inventory value.
- Expense Ratio (`er`): expenses divided by current sales.
- Stock Coverage Period (`scp`): stock on hand divided by average daily sales quantity.
- Business Health Score (`bhs`): weighted score derived from normalized RGR, ITR, and ER.

Period handling:

- `daily`: rolling 7-day window.
- `weekly`: current week vs previous week.
- `monthly`: current month vs prior 30-day comparison.

Snapshot behavior:

- Updates today’s snapshot when one already exists and `force_new` is false.
- Creates a new snapshot otherwise.
- Clears AI summary on update so a fresh summary can be regenerated.

### Business Health Score methodology

The BHS combines normalized metrics:

- `rgr_norm = clamp((rgr + 0.1) / 0.5, 0, 1)`
- `itr_norm = clamp(itr / 5, 0, 1)`
- `er_norm = clamp(er / 0.5, 0, 1)`

Then:

$$
BHS = 100 \times (0.4 \cdot ITR_{norm} + 0.35 \cdot RGR_{norm} + 0.25 \cdot (1 - ER_{norm}))
$$

## 7. Rule Engine Methodology

`AnalyticsService.run_rule_engine(user, snapshot)` creates operational alerts from business conditions.

Rules:

- Low stock alerts when a product reaches or drops below reorder point.
- Urgent reorder alerts when stock coverage is too low.
- Slow-moving inventory alerts when turnover is below threshold.
- Expense spike alerts when expense ratio exceeds threshold.
- Sales decline alerts when revenue growth falls below threshold.
- Pricing recommendation alerts when product margin is below minimum profit margin.

Thresholds:

- `SCP_URGENT_DAYS`
- `ITR_SLOW_THRESHOLD`
- `ER_SPIKE_THRESHOLD`
- `RGR_DECLINE_THRESHOLD`
- `MIN_PROFIT_MARGIN`

If a user-specific threshold exists in `ThresholdConfig`, it overrides the default.

## 8. Store Integration Methodology

Store integration is implemented in `dashboard.views.sync_store_data` using a platform adapter pattern.

### Integration setup

- Users save `store_name`, `platform_type`, `store_url`, and `api_key` in `StoreIntegration`.
- A `StoreIntegration` row is created or fetched with `get_or_create(user=request.user)`.
- After saving, the UI redirects to immediate sync.

### Supported platforms

- `custom`: JSON server style API, used for WonderToyz-style stores.
- `woocommerce`: WooCommerce REST API.
- `shopify`: Shopify Admin API.
- `daraz`: placeholder only, currently returns a “coming soon” message.

### Sync workflow

1. Load the user’s `StoreIntegration` record.
2. Resolve the platform and store URL.
3. Fetch orders through the matching adapter.
4. Normalize orders into a common shape: SKU, quantity, timestamp, and price.
5. Match each order to a local `Product` by SKU.
6. Create a `Transaction` if the order is not already recorded.
7. Decrement stock for the product.
8. Update `last_synced`.
9. Recalculate KPIs.

### Adapter details

- `_fetch_custom_orders(store_url)`: pulls JSON orders directly.
- `_fetch_woocommerce_orders(store_url, api_key)`: calls WooCommerce `/wp-json/wc/v3/orders` and flattens line items.
- `_fetch_shopify_orders(store_url, api_key)`: calls Shopify `/admin/api/2024-01/orders.json` and flattens line items.

## 9. AI Layer Methodology

The AI layer is implemented as a singleton service in `apps/ai_layer/services.py`.

### `AIService`

Important behavior:

- Uses an environment variable `GROQ_API_KEY`.
- Calls the Groq OpenAI-compatible chat completions endpoint.
- Keeps a short cooldown window after failures or rate limits.
- Caches successful responses by cache key.
- Returns a fallback HTML summary when the AI is unavailable.

### `generate_business_summary(snapshot, alerts)`

- Builds a prompt from KPI values and recent alerts.
- Requests a concise HTML summary suitable for rendering in the dashboard or PDF export.

### `chat_api(request)`

- Builds a full business context from the user’s products, sales breakdown, finances, latest KPI snapshot, and recent transactions.
- Sends that context to `AIService.generate_content()`.
- Returns a JSON response with the AI answer.

## 10. Reporting Methodology

### Dashboard charts

- Daily chart data covers the last 14 days.
- Monthly chart data covers the last 6 months.
- Revenue, expenses, COGS, and profit are calculated per bucket.

### PDF export

- `BusinessReportPDF` customizes header and footer.
- The PDF includes KPI values and the AI-generated summary.
- If the AI summary cannot be rendered as HTML, the code falls back to plain text after stripping tags.

## 11. Data Safety and Multi-Tenancy Approach

The project keeps data isolated per user by filtering nearly all queries with `user_id=request.user.id` or `user=request.user`.

This reduces cross-account leakage risk and keeps dashboards, alerts, products, and financial records scoped to the current business owner.

## 12. What Is Implemented

- Authentication and onboarding
- Business profile storage
- Product catalog and stock updates
- Sales and expense logging
- KPI calculation and report history
- Alert creation and manual resolution
- Store sync for custom JSON, WooCommerce, and Shopify
- AI summaries and business chat
- PDF report export

## 13. Notes And Gaps

- `ai_layer/models.py` is empty; the AI layer is service-based only.
- Daraz integration is declared but not implemented beyond a placeholder message.
- The repository README text appears to be out of sync with the code in one place: the implementation uses `GROQ_API_KEY` and Groq’s API, not Gemini.
- I did not find a `proposal.txt` file in the workspace, so this documentation reflects the code that is actually present.

## 14. Suggested Reading Order

If you want to understand the project quickly, read in this order:

1. `accounts/views.py`
2. `inventory/views.py`
3. `finance/views.py`
4. `dashboard/services.py`
5. `dashboard/views.py`
6. `ai_layer/services.py`
7. `ai_layer/views.py`

That sequence follows the real user journey from signup to inventory, transactions, automation, dashboard, and AI output.