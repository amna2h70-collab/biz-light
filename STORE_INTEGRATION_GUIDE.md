# Store Integration Guide

## What This Feature Does

The store integration feature connects Biz-Light to an external ecommerce or custom store system and pulls orders into the platform as internal sales transactions. It also keeps product stock in sync and triggers a KPI refresh after syncing.

In practice, this means:

- external orders become `Transaction` records
- product stock is reduced automatically
- the dashboard KPIs are recalculated
- the latest sync time is stored on the integration record

## Where It Lives In The Code

The feature is centered in the dashboard app:

- model: `dashboard.models.StoreIntegration`
- settings view: `dashboard.views.integration_settings`
- sync view: `dashboard.views.sync_store_data`
- adapter helpers: `_fetch_custom_orders`, `_fetch_woocommerce_orders`, `_fetch_shopify_orders`

The route map is:

- `/dashboard/integration/`
- `/dashboard/sync-store/`

## The Data Model

### `StoreIntegration`

This model stores the connection details for one user.

Fields:

- `user`: one-to-one link to the authenticated user
- `store_name`: display name for the store
- `platform_type`: selected integration type
- `store_url`: base API URL or orders endpoint
- `api_key`: secret token or API credentials
- `created_at`: creation timestamp
- `last_synced`: last successful sync timestamp

### Supported platform types

The current choices are:

- `custom`: custom JSON API, used for WonderToyz or a JSON server style store
- `shopify`: Shopify Admin API
- `woocommerce`: WooCommerce REST API
- `daraz`: listed as an option, but not implemented yet beyond a message saying it is coming soon

## How Setup Works

The integration is configured from the dashboard integration page.

### `integration_settings(request)`

This view does the following:

1. creates or loads the current user’s `StoreIntegration` record
2. shows the current saved values in the form
3. accepts `store_name`, `platform_type`, `store_url`, and `api_key`
4. saves those values for the user
5. redirects to immediate sync after a successful save

If any required field is missing, it returns an error message and keeps the user on the settings page.

## How Sync Works

### `sync_store_data(request)`

This is the main sync workflow.

The process is:

1. load the current user’s `StoreIntegration` record
2. verify that a store URL exists
3. pick the correct platform adapter based on `platform_type`
4. fetch remote orders
5. normalize the remote order data into a common internal shape
6. match each order SKU to a local `Product`
7. create a `Transaction` with type `SALE`
8. reduce local stock for the sold quantity
9. store the latest sync time in `last_synced`
10. recalculate KPIs by calling `AnalyticsService.calculate_kpis(request.user)`

If the user has not configured an integration yet, the system sends them back to the integration page with a warning message.

## Platform Adapters

The sync implementation uses a simple adapter pattern. Each platform has one fetch function that returns a normalized list of orders.

### 1. Custom JSON API

Helper: `_fetch_custom_orders(store_url)`

Used for:

- custom stores
- WonderToyz style JSON server setups

How it works:

- sends a GET request directly to the configured URL
- expects the response body to be JSON
- returns the raw order list

Notes:

- in the dashboard sync flow, the code also tries to fetch products from a related `/products` endpoint when the platform is `custom`
- if products are returned, missing local products are created automatically using the SKU

### 2. WooCommerce

Helper: `_fetch_woocommerce_orders(store_url, api_key)`

Used for:

- WooCommerce stores

How it works:

- parses the `api_key` field as `consumer_key:consumer_secret` when possible
- calls the WooCommerce orders endpoint under `/wp-json/wc/v3/orders`
- requests orders with `status=processing`
- converts each order line item into the internal order format

Normalized output includes:

- `id`
- `sku`
- `name`
- `price`
- `quantity`
- `status`

### 3. Shopify

Helper: `_fetch_shopify_orders(store_url, api_key)`

Used for:

- Shopify stores

How it works:

- sends a GET request to the Shopify Admin API orders endpoint
- uses the API token in the `X-Shopify-Access-Token` header
- requests open orders
- converts each line item into the internal order format

Normalized output includes the same shape used by the other adapters.

### 4. Daraz

Current state:

- shown in the UI as a choice
- not yet implemented in sync logic
- when selected, the sync view shows a message that it is coming soon

## How Internal Records Are Created

After orders are fetched and normalized, the platform creates or updates local records.

### Product matching

Each order is matched by `sku` against an existing `Product` owned by the user.

If the product does not exist:

- for custom sync, the code may create products from the related store product feed
- for WooCommerce and Shopify sync, unmatched SKUs are skipped

### Transaction creation

For each matched order, the system creates a `Transaction` record with:

- `user`
- `product`
- `type='SALE'`
- `quantity`
- `total_amount`

If the order includes a timestamp, the sync logic checks for duplicates before inserting and uses the remote timestamp on the saved transaction.

### Stock updates

When a transaction is created:

- the product’s `stock_level` is reduced by the sold quantity
- the updated stock is saved in the database

### KPI refresh

After sync completes successfully:

- `StoreIntegration.last_synced` is updated
- `AnalyticsService.calculate_kpis(request.user)` is called

That refresh updates the dashboard with the latest sales, expenses, and stock-based metrics.

## How It Connects To The Rest Of The Platform

Store integration is not isolated. It feeds the rest of Biz-Light:

- the dashboard uses the new transactions to update KPIs
- inventory reflects reduced stock after orders are synced
- automation can create low-stock alerts when stock falls below reorder thresholds
- AI summaries use the refreshed KPI snapshot and recent alerts

## Important Implementation Details

- The code normalizes `localhost` to `127.0.0.1` during sync to avoid Windows networking issues.
- The custom platform sync path can also pull product data and auto-create local products from remote SKUs.
- Sync is user-scoped, so one user’s store data does not overwrite another user’s data.
- `daraz` is declared in the model but not yet wired to an API fetcher.

## Summary

Store integration in Biz-Light is a user-configured connector that pulls external orders into the internal sales ledger, updates inventory stock, and refreshes business analytics. The current implementation supports custom JSON stores, WooCommerce, and Shopify, with Daraz reserved for a future adapter.