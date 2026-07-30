#!/usr/bin/env python3
"""
Tapedeck — authenticated venue adapters.

Three brokers, one per credential scheme you might actually hold:

    kraken              KRAKEN_API_KEY, KRAKEN_API_SECRET
                        HMAC-SHA512 over the nonce'd POST body.

    coinbase-exchange   CB_EXCHANGE_KEY, CB_EXCHANGE_SECRET, CB_EXCHANGE_PASSPHRASE
                        HMAC-SHA256. This is the institutional "Exchange"/ex-Pro
                        product — the same host Tapedeck already reads candles
                        from. Most retail accounts do NOT have one.

    coinbase-advanced   CB_CDP_KEY_NAME, CB_CDP_PRIVATE_KEY
                        ES256 JWT per request. This is what an ordinary Coinbase
                        account gets. ECDSA is not in the standard library, so
                        this adapter — and only this adapter — needs
                        `pip install "PyJWT[crypto]"`.

Credentials are read from the environment and nowhere else. Not from a CLI
argument (those land in shell history and in `ps` output for every user on the
box), not from a file in the repo. `credentials_present()` reports what it can
see without ever printing a value.

Scope: these adapters call balance, product, order-placement, order-status and
cancel endpoints. There is no withdrawal or transfer call in this file. Give the
key trade permission and nothing more — no venue requires withdrawal permission
to place an order, and a trading key that cannot move coins off the exchange is a
categorically smaller problem if it leaks.

VERIFICATION STATUS: the signing schemes and request shapes here follow each
venue's documented API, and the selftest pins them against fixed vectors so they
cannot drift silently. They have NOT been exercised against a funded live account
from this repo — nobody's keys were available, and inventing an "it works" claim
about an order path would be the single most dangerous thing this project could
say. Run `--mode shadow` first: it authenticates, reads your real balances and
market rules, and prints the orders it would have sent without sending them.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from broker import (BUY, SELL, Broker, BrokerError, Fill, Market, Order,
                    Rejected, round_price)

UA = "tapedeck/1.0"
TIMEOUT = 20


# ---------------------------------------------------------------- http
def _request(method, url, headers=None, body=None, timeout=TIMEOUT):
    """
    One HTTP call. Returns parsed JSON.

    A 4xx body is read and included in the error: venues put the actual reason
    ("Insufficient funds", "Order size below minimum") in the body, and throwing
    it away turns a five-second fix into an afternoon.
    """
    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method,
                                 headers=dict({"User-Agent": UA}, **(headers or {})))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:400]
        except Exception:                       # noqa: BLE001 - never mask the HTTP error
            pass
        raise BrokerError("%s %s -> HTTP %s %s" % (method, _safe(url), exc.code, detail))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise BrokerError("%s %s -> %s" % (method, _safe(url), exc))
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        raise BrokerError("%s %s -> non-JSON response %r" % (method, _safe(url), raw[:200]))


def _safe(url):
    """URL without its query string — query strings can carry key material."""
    return url.split("?")[0]


def _step(decimals):
    return float("1e-%d" % int(decimals)) if decimals else 1.0


# ---------------------------------------------------------------- kraken
class KrakenBroker(Broker):
    """
    Kraken spot.

    Signing (documented scheme):
        nonce   = always-increasing integer, milliseconds is fine
        post    = urlencode({nonce, **params})
        message = path.encode() + sha256(nonce + post)
        sign    = base64(hmac_sha512(base64decode(secret), message))
        headers = API-Key, API-Sign

    NONCE WARNING: the nonce must strictly increase *per key*. Two processes
    sharing one key will trip over each other and start getting "Invalid nonce"
    — use a separate API key per running instance.

    Idempotency rides on `userref`, Kraken's own client reference. It is a signed
    32-bit integer, not a string, so the client id is folded down to 31 bits.
    `validate=true` gives a real dry run, which `preflight()` uses.
    """

    name = "kraken"
    live = True
    can_short = False               # spot only; no margin path in this project
    BASE = "https://api.kraken.com"

    def __init__(self, key=None, secret=None):
        self.key = key or os.environ.get("KRAKEN_API_KEY", "")
        secret = secret or os.environ.get("KRAKEN_API_SECRET", "")
        if not self.key or not secret:
            raise BrokerError("kraken needs KRAKEN_API_KEY and KRAKEN_API_SECRET "
                              "in the environment")
        try:
            self._secret = base64.b64decode(secret)
        except Exception:
            raise BrokerError("KRAKEN_API_SECRET is not valid base64 — copy it "
                              "again from the venue, it is the 'Private key' field")
        self._last_nonce = 0
        self._pairs = None

    # -- signing -------------------------------------------------------
    def _nonce(self):
        nonce = int(time.time() * 1000)
        if nonce <= self._last_nonce:           # same millisecond, or a clock step back
            nonce = self._last_nonce + 1
        self._last_nonce = nonce
        return nonce

    def sign(self, path, params, nonce=None):
        """Exposed for the selftest to pin against a fixed vector."""
        payload = dict(params)
        payload["nonce"] = nonce if nonce is not None else self._nonce()
        post = urllib.parse.urlencode(payload)
        digest = hashlib.sha256(("%s%s" % (payload["nonce"], post)).encode("utf-8")).digest()
        mac = hmac.new(self._secret, path.encode("utf-8") + digest, hashlib.sha512)
        return post, base64.b64encode(mac.digest()).decode("ascii")

    def _private(self, method, params=None):
        path = "/0/private/" + method
        post, signature = self.sign(path, params or {})
        data = _request("POST", self.BASE + path, headers={
            "API-Key": self.key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded",
        }, body=post)
        errors = data.get("error") or []
        if errors:
            joined = "; ".join(errors)
            if "Insufficient funds" in joined or "Invalid arguments:volume" in joined:
                raise Rejected("kraken: %s" % joined)
            raise BrokerError("kraken %s: %s" % (method, joined))
        return data.get("result") or {}

    def _public(self, method, params=None):
        url = self.BASE + "/0/public/" + method
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = _request("GET", url)
        if data.get("error"):
            raise BrokerError("kraken %s: %s" % (method, "; ".join(data["error"])))
        return data.get("result") or {}

    # -- reference data ------------------------------------------------
    def _altname(self, product):
        base, _, quote = product.partition("-")
        base = {"BTC": "XBT"}.get(base, base)
        return base + quote

    def market(self, product):
        if self._pairs is None:
            self._pairs = self._public("AssetPairs")
        want = self._altname(product)
        for _, row in self._pairs.items():
            if row.get("altname") != want:
                continue
            base, _, quote = product.partition("-")
            return Market(product, base, quote,
                          min_size=float(row.get("ordermin") or 0) or 0.0001,
                          size_step=_step(row.get("lot_decimals", 8)),
                          price_step=_step(row.get("pair_decimals", 2)))
        raise Rejected("kraken does not list %s (looked for pair %r)" % (product, want))

    def ticker(self, product):
        result = self._public("Ticker", {"pair": self._altname(product)})
        for _, row in result.items():
            return float(row["c"][0])           # c = last trade [price, lot volume]
        raise BrokerError("kraken returned no ticker for %s" % product)

    def balances(self):
        raw = self._private("Balance")
        out = {}
        for code, amount in raw.items():
            # Kraken's own asset codes: XXBT, ZUSD, XETH...
            name = code
            if len(code) == 4 and code[0] in "XZ":
                name = code[1:]
            out[{"XBT": "BTC"}.get(name, name)] = float(amount)
        return out

    # -- orders --------------------------------------------------------
    @staticmethod
    def _userref(cid):
        """client id -> signed 31-bit int, which is what `userref` accepts."""
        return int(hashlib.sha256(cid.encode("utf-8")).hexdigest()[:8], 16) & 0x7FFFFFFF

    def _add_order(self, product, side, qty, cid, ordertype="market",
                   price=None, validate=False):
        market = self.market(product)
        params = {
            "pair": self._altname(product),
            "type": side,
            "ordertype": ordertype,
            "volume": _fmt(qty, market.size_step),
            "userref": self._userref(cid),
        }
        if price is not None:
            params["price"] = _fmt(round_price(price, market.price_step), market.price_step)
        if validate:
            params["validate"] = "true"
        return self._private("AddOrder", params)

    def preflight(self, product, side, qty, cid):
        """Kraken's own dry run — validates size, increments and funds, sends nothing."""
        result = self._add_order(product, side, qty, cid, validate=True)
        return (result.get("descr") or {}).get("order", "validated")

    def market_order(self, product, side, qty, cid):
        result = self._add_order(product, side, qty, cid, ordertype="market")
        txids = result.get("txid") or []
        if not txids:
            raise BrokerError("kraken accepted the order but returned no txid: %r" % result)
        return self._await_fill(txids[0], product, side, qty, cid)

    def _await_fill(self, txid, product, side, qty, cid, tries=12):
        """
        A market order is acknowledged before it is filled, so ask what happened.

        Never assume the ack price. If the order is still open after the poll
        window, that is reported rather than guessed — an unknown fill price with
        a real position behind it is exactly the state a human needs to see.
        """
        for attempt in range(tries):
            info = (self._private("QueryOrders", {"txid": txid}) or {}).get(txid) or {}
            status = info.get("status")
            if status in ("closed", "canceled", "expired"):
                executed = float(info.get("vol_exec") or 0)
                if executed <= 0:
                    raise Rejected("kraken order %s ended %s with nothing filled"
                                   % (txid, status))
                cost = float(info.get("cost") or 0)
                price = (cost / executed) if executed else float(info.get("price") or 0)
                return Fill(cid, txid, product, side, executed, price,
                            float(info.get("fee") or 0), time.time())
            time.sleep(min(0.4 * (attempt + 1), 2.0))
        raise BrokerError("kraken order %s still open after the poll window — a "
                          "position may exist. Check the venue before trading again."
                          % txid)

    def stop_order(self, product, side, qty, stop_price, cid):
        result = self._add_order(product, side, qty, cid, ordertype="stop-loss",
                                 price=stop_price)
        txids = result.get("txid") or []
        market = self.market(product)
        return Order(cid, txids[0] if txids else "", product, side, "stop", qty,
                     round_price(stop_price, market.price_step), "open")

    def cancel(self, venue_id, product=None):
        try:
            self._private("CancelOrder", {"txid": venue_id})
        except BrokerError as exc:
            if "Unknown order" not in str(exc):   # already gone is the goal, not a failure
                raise

    def open_orders(self, product=None):
        raw = (self._private("OpenOrders") or {}).get("open") or {}
        out = []
        for txid, info in raw.items():
            descr = info.get("descr") or {}
            pair = descr.get("pair", "")
            if product and pair.replace("/", "").upper() != self._altname(product).upper():
                continue
            out.append(Order("", txid, product or pair, descr.get("type", ""),
                             descr.get("ordertype", ""), float(info.get("vol") or 0),
                             float(descr.get("price") or 0) or None, "open"))
        return out


def _fmt(value, step):
    """Decimal string at the venue's precision — never exponent notation."""
    places = max(0, len(("%.10f" % step).rstrip("0").split(".")[1])) if step < 1 else 0
    return "%.*f" % (places, value)


# ---------------------------------------------------------------- coinbase exchange
class CoinbaseExchangeBroker(Broker):
    """
    Coinbase Exchange (the institutional product, formerly Coinbase Pro).

    Signing (documented scheme):
        message = timestamp + METHOD + request_path + body
        sign    = base64(hmac_sha256(base64decode(secret), message))
        headers = CB-ACCESS-KEY, CB-ACCESS-SIGN, CB-ACCESS-TIMESTAMP,
                  CB-ACCESS-PASSPHRASE

    `client_oid` must be a UUID here, so the deterministic client id is folded
    into UUID shape — same input, same UUID, so a retry is still a duplicate the
    venue can reject.
    """

    name = "coinbase-exchange"
    live = True
    can_short = False
    BASE = "https://api.exchange.coinbase.com"

    def __init__(self, key=None, secret=None, passphrase=None):
        self.key = key or os.environ.get("CB_EXCHANGE_KEY", "")
        secret = secret or os.environ.get("CB_EXCHANGE_SECRET", "")
        self.passphrase = passphrase or os.environ.get("CB_EXCHANGE_PASSPHRASE", "")
        if not (self.key and secret and self.passphrase):
            raise BrokerError("coinbase-exchange needs CB_EXCHANGE_KEY, "
                              "CB_EXCHANGE_SECRET and CB_EXCHANGE_PASSPHRASE")
        try:
            self._secret = base64.b64decode(secret)
        except Exception:
            raise BrokerError("CB_EXCHANGE_SECRET is not valid base64")

    def sign(self, timestamp, method, path, body=""):
        """Exposed for the selftest to pin against a fixed vector."""
        message = "%s%s%s%s" % (timestamp, method.upper(), path, body)
        mac = hmac.new(self._secret, message.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("ascii")

    def _call(self, method, path, payload=None):
        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        timestamp = "%.3f" % time.time()
        headers = {
            "CB-ACCESS-KEY": self.key,
            "CB-ACCESS-SIGN": self.sign(timestamp, method, path, body),
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        try:
            return _request(method, self.BASE + path, headers=headers, body=body or None)
        except BrokerError as exc:
            text = str(exc)
            if "Insufficient funds" in text or "size is too small" in text:
                raise Rejected(text)
            raise

    @staticmethod
    def _client_oid(cid):
        digest = hashlib.sha256(cid.encode("utf-8")).hexdigest()[:32]
        return "-".join((digest[:8], digest[8:12], digest[12:16],
                         digest[16:20], digest[20:32]))

    def market(self, product):
        row = _request("GET", "%s/products/%s" % (self.BASE, product))
        base, _, quote = product.partition("-")
        increment = float(row.get("base_increment") or 0.00000001)
        return Market(product, base, quote,
                      min_size=float(row.get("base_min_size") or increment),
                      size_step=increment,
                      price_step=float(row.get("quote_increment") or 0.01))

    def ticker(self, product):
        row = _request("GET", "%s/products/%s/ticker" % (self.BASE, product))
        return float(row["price"])

    def balances(self):
        out = {}
        for row in self._call("GET", "/accounts") or []:
            available = float(row.get("available") or 0)
            if available:
                out[row["currency"]] = available
        return out

    def market_order(self, product, side, qty, cid):
        market = self.market(product)
        row = self._call("POST", "/orders", {
            "type": "market",
            "side": side,
            "product_id": product,
            "size": _fmt(qty, market.size_step),
            "client_oid": self._client_oid(cid),
        })
        return self._await_fill(row.get("id", ""), product, side, qty, cid)

    def _await_fill(self, order_id, product, side, qty, cid, tries=12):
        for attempt in range(tries):
            row = self._call("GET", "/orders/" + order_id)
            if row.get("status") in ("done", "settled"):
                executed = float(row.get("filled_size") or 0)
                spent = float(row.get("executed_value") or 0)
                if executed <= 0:
                    raise Rejected("coinbase order %s finished unfilled" % order_id)
                return Fill(cid, order_id, product, side, executed,
                            spent / executed, float(row.get("fill_fees") or 0),
                            time.time())
            if row.get("status") == "rejected":
                raise Rejected("coinbase rejected order %s: %s"
                               % (order_id, row.get("reject_reason")))
            time.sleep(min(0.4 * (attempt + 1), 2.0))
        raise BrokerError("coinbase order %s still open after the poll window — a "
                          "position may exist. Check the venue before trading again."
                          % order_id)

    def stop_order(self, product, side, qty, stop_price, cid):
        market = self.market(product)
        price = round_price(stop_price, market.price_step)
        row = self._call("POST", "/orders", {
            "type": "market",                   # stop-market: exit is certain, price isn't
            "side": side,
            "product_id": product,
            "size": _fmt(qty, market.size_step),
            "stop": "loss" if side == SELL else "entry",
            "stop_price": _fmt(price, market.price_step),
            "client_oid": self._client_oid(cid),
        })
        return Order(cid, row.get("id", ""), product, side, "stop", qty, price, "open")

    def cancel(self, venue_id, product=None):
        try:
            self._call("DELETE", "/orders/" + venue_id)
        except BrokerError as exc:
            if "NotFound" not in str(exc) and "404" not in str(exc):
                raise

    def open_orders(self, product=None):
        path = "/orders?status=open"
        if product:
            path += "&product_id=" + product
        out = []
        for row in self._call("GET", path) or []:
            out.append(Order("", row.get("id", ""), row.get("product_id", ""),
                             row.get("side", ""), row.get("type", ""),
                             float(row.get("size") or 0),
                             float(row.get("price") or 0) or None, "open"))
        return out


# ---------------------------------------------------------------- coinbase advanced
class CoinbaseAdvancedBroker(Broker):
    """
    Coinbase Advanced Trade — what an ordinary retail Coinbase account has.

    Auth is a short-lived ES256 JWT per request, signed with a CDP private key.
    ECDSA is not in the standard library, so this is the one adapter with a
    dependency:

        pip install "PyJWT[crypto]"

    CB_CDP_KEY_NAME   the key's full resource name (organizations/.../apiKeys/...)
    CB_CDP_PRIVATE_KEY the EC private key PEM. Newlines may be written as \\n.

    The protective stop here is a stop-LIMIT, because that is what this API
    exposes. A stop-limit can be skipped by a fast gap in a way a stop-market
    cannot, so the limit is placed `STOP_LIMIT_SLIP` below the trigger to give it
    room to fill. That is a real difference in the protection you are getting,
    which is why it is stated here and reported in the run's caveats rather than
    left for you to discover during a flash crash.
    """

    name = "coinbase-advanced"
    live = True
    can_short = False
    HOST = "api.coinbase.com"
    BASE = "https://api.coinbase.com"
    PREFIX = "/api/v3/brokerage"
    STOP_LIMIT_SLIP = 0.005         # 0.5% below the trigger for a sell stop

    def __init__(self, key_name=None, private_key=None):
        self.key_name = key_name or os.environ.get("CB_CDP_KEY_NAME", "")
        self._pem = (private_key or os.environ.get("CB_CDP_PRIVATE_KEY", "")).replace("\\n", "\n")
        if not self.key_name or not self._pem:
            raise BrokerError("coinbase-advanced needs CB_CDP_KEY_NAME and "
                              "CB_CDP_PRIVATE_KEY")
        try:
            import jwt                                    # noqa: F401
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            raise BrokerError(
                "coinbase-advanced signs with ES256, which the standard library "
                "cannot do.\n  pip install \"PyJWT[crypto]\"\n"
                "Every other part of Tapedeck stays dependency-free; only this "
                "adapter needs it.")
        try:
            self._loaded = serialization.load_pem_private_key(
                self._pem.encode("utf-8"), password=None)
        except Exception as exc:
            raise BrokerError("CB_CDP_PRIVATE_KEY is not a readable PEM private "
                              "key (%s)" % exc)

    def _token(self, method, path):
        import secrets

        import jwt
        now = int(time.time())
        return jwt.encode(
            {"sub": self.key_name, "iss": "cdp", "nbf": now, "exp": now + 120,
             "uri": "%s %s%s" % (method.upper(), self.HOST, path)},
            self._loaded, algorithm="ES256",
            headers={"kid": self.key_name, "nonce": secrets.token_hex(16)})

    def _call(self, method, path, payload=None):
        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        headers = {"Authorization": "Bearer " + self._token(method, path),
                   "Content-Type": "application/json"}
        try:
            return _request(method, self.BASE + path, headers=headers, body=body or None)
        except BrokerError as exc:
            if "INSUFFICIENT_FUND" in str(exc) or "TOO_SMALL" in str(exc):
                raise Rejected(str(exc))
            raise

    def market(self, product):
        row = self._call("GET", "%s/products/%s" % (self.PREFIX, product))
        base, _, quote = product.partition("-")
        increment = float(row.get("base_increment") or 0.00000001)
        return Market(product, base, quote,
                      min_size=float(row.get("base_min_size") or increment),
                      size_step=increment,
                      price_step=float(row.get("quote_increment") or 0.01))

    def ticker(self, product):
        row = self._call("GET", "%s/products/%s" % (self.PREFIX, product))
        return float(row.get("price") or 0)

    def balances(self):
        out = {}
        for row in (self._call("GET", self.PREFIX + "/accounts") or {}).get("accounts") or []:
            available = float(((row.get("available_balance") or {}).get("value")) or 0)
            if available:
                out[row.get("currency", "?")] = available
        return out

    def market_order(self, product, side, qty, cid):
        market = self.market(product)
        row = self._call("POST", self.PREFIX + "/orders", {
            "client_order_id": cid,
            "product_id": product,
            "side": side.upper(),
            "order_configuration": {
                "market_market_ioc": {"base_size": _fmt(qty, market.size_step)}},
        })
        if not row.get("success", False):
            raise Rejected("coinbase-advanced refused the order: %s"
                           % json.dumps(row.get("error_response") or row)[:300])
        order_id = ((row.get("success_response") or {}).get("order_id")
                    or (row.get("order_id") or ""))
        return self._await_fill(order_id, product, side, qty, cid)

    def _await_fill(self, order_id, product, side, qty, cid, tries=12):
        for attempt in range(tries):
            order = (self._call("GET", "%s/orders/historical/%s"
                                % (self.PREFIX, order_id)) or {}).get("order") or {}
            status = order.get("status")
            if status == "FILLED":
                executed = float(order.get("filled_size") or 0)
                price = float(order.get("average_filled_price") or 0)
                fee = float(order.get("total_fees") or 0)
                if executed <= 0 or price <= 0:
                    raise Rejected("coinbase-advanced reported FILLED with no size")
                return Fill(cid, order_id, product, side, executed, price, fee, time.time())
            if status in ("CANCELLED", "EXPIRED", "FAILED"):
                raise Rejected("coinbase-advanced order %s ended %s" % (order_id, status))
            time.sleep(min(0.4 * (attempt + 1), 2.0))
        raise BrokerError("coinbase-advanced order %s still open after the poll "
                          "window — a position may exist. Check the venue before "
                          "trading again." % order_id)

    def stop_order(self, product, side, qty, stop_price, cid):
        market = self.market(product)
        trigger = round_price(stop_price, market.price_step)
        # give the limit room to actually fill once the stop trips
        limit = trigger * (1 - self.STOP_LIMIT_SLIP) if side == SELL \
            else trigger * (1 + self.STOP_LIMIT_SLIP)
        row = self._call("POST", self.PREFIX + "/orders", {
            "client_order_id": cid,
            "product_id": product,
            "side": side.upper(),
            "order_configuration": {"stop_limit_stop_limit_gtc": {
                "base_size": _fmt(qty, market.size_step),
                "stop_price": _fmt(trigger, market.price_step),
                "limit_price": _fmt(round_price(limit, market.price_step), market.price_step),
                "stop_direction": ("STOP_DIRECTION_STOP_DOWN" if side == SELL
                                   else "STOP_DIRECTION_STOP_UP"),
            }},
        })
        if not row.get("success", False):
            raise BrokerError("coinbase-advanced refused the protective stop: %s"
                              % json.dumps(row.get("error_response") or row)[:300])
        order_id = ((row.get("success_response") or {}).get("order_id") or "")
        return Order(cid, order_id, product, side, "stop", qty, trigger, "open")

    def cancel(self, venue_id, product=None):
        try:
            self._call("POST", self.PREFIX + "/orders/batch_cancel",
                       {"order_ids": [venue_id]})
        except BrokerError as exc:
            if "UNKNOWN_CANCEL_ORDER" not in str(exc):
                raise

    def open_orders(self, product=None):
        path = self.PREFIX + "/orders/historical/batch?order_status=OPEN"
        if product:
            path += "&product_id=" + product
        out = []
        for row in (self._call("GET", path) or {}).get("orders") or []:
            config = row.get("order_configuration") or {}
            leg = (config.get("stop_limit_stop_limit_gtc")
                   or config.get("limit_limit_gtc") or {})
            out.append(Order(row.get("client_order_id", ""), row.get("order_id", ""),
                             row.get("product_id", ""), (row.get("side") or "").lower(),
                             "stop" if "stop_limit" in json.dumps(config) else "limit",
                             float(leg.get("base_size") or 0),
                             float(leg.get("stop_price") or leg.get("limit_price") or 0) or None,
                             "open"))
        return out


# ---------------------------------------------------------------- registry
VENUES = {
    "kraken": KrakenBroker,
    "coinbase-exchange": CoinbaseExchangeBroker,
    "coinbase-advanced": CoinbaseAdvancedBroker,
}

REQUIRED_ENV = {
    "kraken": ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
    "coinbase-exchange": ("CB_EXCHANGE_KEY", "CB_EXCHANGE_SECRET",
                          "CB_EXCHANGE_PASSPHRASE"),
    "coinbase-advanced": ("CB_CDP_KEY_NAME", "CB_CDP_PRIVATE_KEY"),
}


def credentials_present(venue=None):
    """
    Which venues have all their environment variables set.

    Reports presence only — never a value, never a prefix. A "helpfully" truncated
    key in a log is still a leaked key.
    """
    out = {}
    for name, needed in REQUIRED_ENV.items():
        if venue and name != venue:
            continue
        missing = [var for var in needed if not os.environ.get(var)]
        out[name] = {"ready": not missing, "missing": missing}
    return out


def connect(venue):
    """Build a broker for `venue`, or explain exactly what is missing."""
    if venue not in VENUES:
        raise BrokerError("unknown venue %r — have %s"
                          % (venue, ", ".join(sorted(VENUES))))
    state = credentials_present(venue)[venue]
    if not state["ready"]:
        raise BrokerError("%s is missing %s in the environment"
                          % (venue, ", ".join(state["missing"])))
    return VENUES[venue]()


if __name__ == "__main__":
    print("Credential check (presence only — no values are read out):\n")
    for name, state in sorted(credentials_present().items()):
        mark = "ready" if state["ready"] else "missing " + ", ".join(state["missing"])
        print("  %-20s %s" % (name, mark))
    print("\nNothing was sent to any venue by this check.")
