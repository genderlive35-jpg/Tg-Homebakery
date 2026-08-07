import os
import sqlite3
import requests

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DB = "shop.db"
OWNER_ID = int(os.getenv("OWNER_ID", "8693950791"))


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT DEFAULT '',
            image TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins(
            telegram_id INTEGER PRIMARY KEY,
            owner INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute(
        "INSERT OR REPLACE INTO admins(telegram_id, owner) VALUES(?, 1)",
        (OWNER_ID,)
    )

    conn.commit()
    conn.close()


def tg_id():
    try:
        return int(
            request.headers.get(
                "X-Telegram-User-Id",
                "0"
            )
        )
    except:
        return 0


def admin():
    uid = tg_id()

    if not uid:
        return None

    conn = db()

    row = conn.execute(
        "SELECT owner FROM admins WHERE telegram_id=?",
        (uid,)
    ).fetchone()

    conn.close()

    return row


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/admin")
def admin_page():
    return render_template("admin.html")


@app.get("/api/me")
def me():

    row = admin()

    return jsonify(
        id=tg_id(),
        admin=bool(row),
        owner=bool(row and row["owner"])
    )


@app.get("/api/products")
def products():

    conn = db()

    result = [
        dict(x)
        for x in conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        )
    ]

    conn.close()

    return jsonify(result)


@app.post("/api/products")
def add_product():

    if not admin():
        return jsonify(
            error="Нет прав администратора"
        ), 403

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    if not name:
        return jsonify(
            error="Введите название"
        ), 400

    try:
        price = int(
            float(data.get("price", 0))
        )
    except:
        return jsonify(
            error="Неверная цена"
        ), 400

    conn = db()

    conn.execute(
        """
        INSERT INTO products(
            name,
            price,
            description,
            image
        )
        VALUES(?,?,?,?)
        """,
        (
            name,
            price,
            str(data.get("description", "")),
            str(data.get("image", ""))
        )
    )

    conn.commit()
    conn.close()

    return jsonify(ok=True)


@app.delete("/api/products/<int:pid>")
def delete_product(pid):

    if not admin():
        return jsonify(
            error="Нет прав администратора"
        ), 403

    conn = db()

    conn.execute(
        "DELETE FROM products WHERE id=?",
        (pid,)
    )

    conn.commit()
    conn.close()

    return jsonify(ok=True)


@app.get("/api/admins")
def admins():

    row = admin()

    if not row or not row["owner"]:
        return jsonify(
            error="Только владелец может управлять администраторами"
        ), 403

    conn = db()

    result = [
        dict(x)
        for x in conn.execute(
            """
            SELECT telegram_id, owner
            FROM admins
            ORDER BY owner DESC
            """
        )
    ]

    conn.close()

    return jsonify(result)


@app.post("/api/admins")
def add_admin():

    row = admin()

    if not row or not row["owner"]:
        return jsonify(
            error="Только владелец может добавлять администраторов"
        ), 403

    data = request.get_json(silent=True) or {}

    try:
        uid = int(
            data.get("telegram_id", 0)
        )
    except:
        uid = 0

    if not uid:
        return jsonify(
            error="Введите Telegram ID"
        ), 400

    conn = db()

    conn.execute(
        """
        INSERT OR IGNORE INTO admins(
            telegram_id,
            owner
        )
        VALUES(?, 0)
        """,
        (uid,)
    )

    conn.commit()
    conn.close()

    return jsonify(ok=True)


@app.delete("/api/admins/<int:uid>")
def remove_admin(uid):

    row = admin()

    if not row or not row["owner"]:
        return jsonify(
            error="Только владелец может удалять администраторов"
        ), 403

    if uid == OWNER_ID:
        return jsonify(
            error="Владельца удалить нельзя"
        ), 400

    conn = db()

    conn.execute(
        """
        DELETE FROM admins
        WHERE telegram_id=?
        AND owner=0
        """,
        (uid,)
    )

    conn.commit()
    conn.close()

    return jsonify(ok=True)


@app.post("/api/payment-done")
def payment_done():

    data = request.get_json(silent=True) or {}

    cart = data.get("cart", [])
    total = data.get("total", 0)

    if not cart:
        return jsonify(
            error="Корзина пуста"
        ), 400

    token = os.getenv("BOT_TOKEN")

    if not token:
        return jsonify(
            error="BOT_TOKEN не настроен"
        ), 500

    text = "💰 НОВЫЙ ЗАКАЗ\n\n"

    for item in cart:

        text += (
            f"• {item.get('name', 'Товар')} "
            f"— {item.get('price', 0)} ₽\n"
        )

    text += f"\n💵 Итого: {total} ₽"

    try:

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": OWNER_ID,
                "text": text
            },
            timeout=10
        )

        if not response.ok:
            return jsonify(
                error="Telegram не принял сообщение"
            ), 502

    except Exception as error:

        return jsonify(
            error=str(error)
        ), 502

    return jsonify(ok=True)


init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        )
    )
