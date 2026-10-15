"""Local server for Thread Fashion Studio, SQLite persistence, and optional AI Stylist."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import os
import sqlite3
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "thread_ai.db"
SEED_PATH = ROOT / "products_seed.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database and seed the product catalogue on first run."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                rating REAL NOT NULL,
                vibe TEXT NOT NULL,
                tag TEXT NOT NULL,
                color TEXT NOT NULL,
                img TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS favourites (
                product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS style_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                vibe TEXT,
                palette TEXT,
                occasion TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0 and SEED_PATH.exists():
            products = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            conn.executemany("""
                INSERT INTO products (id, name, category, price, rating, vibe, tag, color, img, description)
                VALUES (:id, :name, :category, :price, :rating, :vibe, :tag, :color, :img, :desc)
            """, products)
        conn.commit()


def product_rows():
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, category, price, rating, vibe, tag, color, img, description AS desc FROM products ORDER BY id").fetchall()
        return [dict(row) for row in rows]


def read_json(handler, max_length=90000):
    length = min(int(handler.headers.get("Content-Length", "0")), max_length)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/products":
            return self.respond(200, {"products": product_rows()})
        if path == "/api/saved":
            with get_db() as conn:
                ids = [r[0] for r in conn.execute("SELECT product_id FROM favourites ORDER BY saved_at, product_id")]
            return self.respond(200, {"ids": ids})
        if path == "/api/profile":
            with get_db() as conn:
                row = conn.execute("SELECT vibe, palette, occasion FROM style_profile WHERE id = 1").fetchone()
            return self.respond(200, {"profile": dict(row) if row else None})
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            data = read_json(self)
            if path == "/api/saved":
                ids = data.get("ids", [])
                if not isinstance(ids, list):
                    return self.respond(400, {"error": "ids must be a list"})
                clean_ids = sorted({int(x) for x in ids if str(x).isdigit()})
                with get_db() as conn:
                    conn.execute("DELETE FROM favourites")
                    conn.executemany("INSERT OR IGNORE INTO favourites (product_id) VALUES (?)", [(x,) for x in clean_ids])
                    conn.commit()
                return self.respond(200, {"ok": True, "ids": clean_ids})

            if path == "/api/profile":
                profile = data.get("profile")
                if profile is None:
                    with get_db() as conn:
                        conn.execute("DELETE FROM style_profile WHERE id = 1")
                        conn.commit()
                    return self.respond(200, {"ok": True, "profile": None})
                if not isinstance(profile, dict):
                    return self.respond(400, {"error": "profile must be an object"})
                values = tuple(str(profile.get(k, ""))[:80] for k in ("vibe", "palette", "occasion"))
                with get_db() as conn:
                    conn.execute("""INSERT INTO style_profile (id, vibe, palette, occasion, updated_at)
                        VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(id) DO UPDATE SET vibe=excluded.vibe, palette=excluded.palette,
                        occasion=excluded.occasion, updated_at=CURRENT_TIMESTAMP""", values)
                    conn.commit()
                return self.respond(200, {"ok": True, "profile": dict(zip(("vibe", "palette", "occasion"), values))})

            if path != "/api/stylist":
                return self.respond(404, {"error": "Not found"})
            message = str(data.get("message", ""))[:1200]
            if not message.strip():
                return self.respond(400, {"error": "Please enter a message."})
            if not API_KEY:
                return self.respond(503, {"error": "AI key not configured; use local style matching."})

            # Use the SQLite catalogue as the source of truth for AI product context.
            catalog = product_rows()[:40]
            profile = data.get("profile", {})
            saved_ids = data.get("saved", [])[:40]
            history = data.get("history", [])[-8:]
            saved = [p for p in catalog if p["id"] in saved_ids] if saved_ids and isinstance(saved_ids[0], int) else saved_ids
            system = (
                "You are Thread's friendly, practical AI fashion stylist. Answer clearly and concisely, in a warm non-judgmental tone. "
                "Recommend only products from the provided catalog; do not invent stock or external links. Prices are sample INR prices. "
                "Respect budget and occasion, suggest combinations and explain why they work. Avoid body shaming and rigid appearance rules. "
                "Return valid JSON with keys reply (string) and product_ids (array of integer product IDs, max 3). "
                "User style profile: " + json.dumps(profile, ensure_ascii=False) + "\nSaved pieces: " + json.dumps(saved, ensure_ascii=False) +
                "\nCatalog: " + json.dumps(catalog, ensure_ascii=False)
            )
            msgs = [{"role": "system", "content": system}]
            for item in history:
                role, content = item.get("role"), item.get("content")
                if role in ("user", "assistant") and isinstance(content, str):
                    msgs.append({"role": role, "content": content[:1800]})
            msgs.append({"role": "user", "content": message})
            body = json.dumps({"model": MODEL, "messages": msgs, "temperature": 0.7, "response_format": {"type": "json_object"}}).encode()
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=45) as resp:
                result = json.loads(resp.read().decode())
            parsed = json.loads(result["choices"][0]["message"]["content"])
            reply = str(parsed.get("reply", "Here are a few ideas to try."))[:5000]
            ids = [int(x) for x in parsed.get("product_ids", [])[:3] if str(x).isdigit()]
            return self.respond(200, {"mode": "AI", "reply": reply, "product_ids": ids})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            print("OpenAI API error:", exc.code, detail)
            return self.respond(502, {"error": "The AI service could not respond. Check your API key, API access, and billing."})
        except (ValueError, TypeError, sqlite3.Error) as exc:
            print("Request/database error:", repr(exc))
            return self.respond(400, {"error": "The request or database operation could not be completed."})
        except Exception as exc:
            print("Stylist/server error:", repr(exc))
            return self.respond(500, {"error": "The server had a problem. Please try again."})

    def respond(self, code, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    init_db()
    host, port = "127.0.0.1", int(os.getenv("PORT", "8000"))
    print("\nThread — Fashion Recommendation Studio")
    print(f"SQLite database: {DB_PATH.name}")
    print(f"Open http://{host}:{port} in your browser")
    print("AI mode:", "enabled (OpenAI API)" if API_KEY else "local styling only — set OPENAI_API_KEY to enable AI chat")
    print("Press Ctrl+C to stop the server.\n")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
