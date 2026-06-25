#!/usr/bin/env python3
"""
Shopify integration for Stark Digital.
Set env vars:  SHOPIFY_SHOP=your-store.myshopify.com
               SHOPIFY_TOKEN=shpat_xxxxxxxxxxxx
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN", "")
API_VERSION = "2024-01"


class ShopifyClient:
    def __init__(self, shop=None, token=None):
        self.shop = (shop or SHOPIFY_SHOP).rstrip("/")
        self.token = token or SHOPIFY_TOKEN
        self.base = f"https://{self.shop}/admin/api/{API_VERSION}"

    def _configured(self):
        return bool(self.shop and self.token)

    def _req(self, method, path, data=None):
        if not self._configured():
            raise RuntimeError("SHOPIFY_SHOP and SHOPIFY_TOKEN env vars not set")
        url = self.base + path
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={
                "X-Shopify-Access-Token": self.token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Shopify {e.code}: {body[:300]}")

    # ── products ────────────────────────────────────────────────────────────────
    def list_products(self, limit=10):
        data = self._req("GET", f"/products.json?limit={limit}&status=active")
        return data.get("products", [])

    def get_product(self, product_id):
        data = self._req("GET", f"/products/{product_id}.json")
        return data.get("product", {})

    def create_product(self, title, body_html, price, product_type="Digital",
                       tags="", vendor="Stark Digital"):
        payload = {
            "product": {
                "title": title,
                "body_html": body_html,
                "vendor": vendor,
                "product_type": product_type,
                "tags": tags,
                "variants": [{"price": str(price), "requires_shipping": False}],
                "published": True,
            }
        }
        data = self._req("POST", "/products.json", payload)
        return data.get("product", {})

    def update_product(self, product_id, updates: dict):
        payload = {"product": {"id": product_id, **updates}}
        data = self._req("PUT", f"/products/{product_id}.json", payload)
        return data.get("product", {})

    # ── orders ──────────────────────────────────────────────────────────────────
    def list_orders(self, status="any", limit=20, since_days=7):
        since = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        path = f"/orders.json?status={status}&limit={limit}&created_at_min={since}"
        data = self._req("GET", path)
        return data.get("orders", [])

    def get_order(self, order_id):
        data = self._req("GET", f"/orders/{order_id}.json")
        return data.get("order", {})

    # ── analytics ───────────────────────────────────────────────────────────────
    def sales_summary(self, since_days=7):
        orders = self.list_orders(status="paid", since_days=since_days)
        total_revenue = sum(float(o.get("total_price", 0)) for o in orders)
        total_orders = len(orders)
        avg_order = total_revenue / total_orders if total_orders else 0
        product_counts = {}
        for o in orders:
            for li in o.get("line_items", []):
                name = li.get("title", "Unknown")
                product_counts[name] = product_counts.get(name, 0) + li.get("quantity", 1)
        top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "period_days": since_days,
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order, 2),
            "top_products": [{"name": n, "units": u} for n, u in top_products],
        }

    # ── customers ───────────────────────────────────────────────────────────────
    def list_customers(self, limit=20):
        data = self._req("GET", f"/customers.json?limit={limit}")
        return data.get("customers", [])

    def customer_count(self):
        data = self._req("GET", "/customers/count.json")
        return data.get("count", 0)

    # ── health check ────────────────────────────────────────────────────────────
    def ping(self) -> dict:
        if not self._configured():
            return {"ok": False, "error": "Not configured — set SHOPIFY_SHOP and SHOPIFY_TOKEN"}
        try:
            data = self._req("GET", "/shop.json")
            shop = data.get("shop", {})
            return {
                "ok": True,
                "shop_name": shop.get("name", ""),
                "email": shop.get("email", ""),
                "currency": shop.get("currency", ""),
                "plan": shop.get("plan_name", ""),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── singleton ──────────────────────────────────────────────────────────────────
_client = None


def get_client() -> ShopifyClient:
    global _client
    if _client is None:
        _client = ShopifyClient()
    return _client


def is_configured() -> bool:
    return bool(SHOPIFY_SHOP and SHOPIFY_TOKEN)
