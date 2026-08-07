import os
import sqlite3
import requests

from flask import Flask, request, jsonify, render_template


app = Flask(__name__)

DB = "shop.db"

OWNER_ID = int(
    os.getenv(
        "OWNER_ID",
        "8693950791"
    )
)


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

    # Владелец всегда добавляется
    # как главный администратор.

    conn.execute(
        """
        INSERT OR REPLACE INTO admins(
            telegram_id,
            owner
        )
        VALUES(?, 1)
        """,
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
        """
        SELECT owner
        FROM admins
        WHERE telegram_id=?
        """,
        (uid,)
    ).fetchone()

    conn.close()

    return row


# -------------------------
# СТРАНИЦЫ
# -------------------------

@app.get("/")
def index():

    return render_template(
        "index.html"
    )


@app.get("/admin")
def admin_page():

    return render_template(
        "admin.html"
    )


# -------------------------
# ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ
# -------------------------

@app.get("/api/me")
def me():

    row = admin()

    return jsonify(
        id=tg_id(),
        admin=bool(row),
        owner=bool(
            row and row["owner"]
        )
    )


# -------------------------
# ТОВАРЫ
# -------------------------

@app.get("/api/products")
def products():

    conn = db()

    result = [
        dict(x)
        for x in conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
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


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()


    if not name:

        return jsonify(
            error="Введите название"
        ), 400


    try:

        price = int(
            float(
                data.get(
                    "price",
                    0
                )
            )
        )

    except:

        return jsonify(
            error="Неверная цена"
        ), 400


    description = str(
        data.get(
            "description",
            ""
        )
    )


    image = str(
        data.get(
            "image",
            ""
        )
    )


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
            description,
            image
        )
    )

    conn.commit()
    conn.close()


    return jsonify(
        ok=True
    )


@app.delete("/api/products/<int:pid>")
def delete_product(pid):

    if not admin():

        return jsonify(
            error="Нет прав администратора"
        ), 403


    conn = db()

    conn.execute(
        """
        DELETE FROM products
        WHERE id=?
        """,
        (pid,)
    )

    conn.commit()
    conn.close()


    return jsonify(
        ok=True
    )


# -------------------------
# АДМИНИСТРАТОРЫ
# -------------------------

@app.get("/api/admins")
def admins():

    row = admin()

    if not row or not row["owner"]:

        return jsonify(
            error=(
                "Только владелец может "
                "управлять администраторами"
            )
        ), 403


    conn = db()

    result = [
        dict(x)
        for x in conn.execute(
            """
            SELECT
                telegram_id,
                owner
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
            error=(
                "Только владелец может "
                "добавлять администраторов"
            )
        ), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    try:

        uid = int(
            data.get(
                "telegram_id",
                0
            )
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


    return jsonify(
        ok=True
    )


@app.delete("/api/admins/<int:uid>")
def remove_admin(uid):

    row = admin()

    if not row or not row["owner"]:

        return jsonify(
            error=(
                "Только владелец может "
                "удалять администраторов"
            )
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


    return jsonify(
        ok=True
    )


# -------------------------
# ПОКУПАТЕЛЬ НАЖАЛ
# "Я ОПЛАТИЛ(А)"
# -------------------------

@app.post("/api/payment-done")
def payment_done():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    cart = data.get(
        "cart",
        []
    )


    total = data.get(
        "total",
        0
    )


    buyer = data.get(
        "buyer",
        {}
    )


    if not cart:

        return jsonify(
            error="Корзина пуста"
        ), 400


    # Данные покупателя

    buyer_id = buyer.get(
        "id"
    )


    first_name = str(
        buyer.get(
            "first_name",
            ""
        )
    ).strip()


    last_name = str(
        buyer.get(
            "last_name",
            ""
        )
    ).strip()


    username = str(
        buyer.get(
            "username",
            ""
        )
    ).strip()


    full_name = (
        first_name
        + " "
        + last_name
    ).strip()


    if not full_name:

        full_name = (
            "Не указано"
        )


    if username:

        username_text = (
            "@"
            + username.lstrip("@")
        )

    else:

        username_text = (
            "не указан"
        )


    if not buyer_id:

        buyer_id_text = (
            "не получен"
        )

    else:

        buyer_id_text = str(
            buyer_id
        )


    # Формируем сообщение
    # ТОЧНО в нужном формате.

    text = (
        "💰 ПОКУПАТЕЛЬ СООБЩИЛ ОБ ОПЛАТЕ\n\n"
    )

    text += (
        f"👤 Покупатель: {full_name}\n"
    )

    text += (
        f"🔗 Username: {username_text}\n"
    )

    text += (
        f"🆔 Telegram ID: {buyer_id_text}\n\n"
    )

    text += (
        "📦 Заказ:\n"
    )


    for item in cart:

        item_name = item.get(
            "name",
            "Товар"
        )

        item_price = item.get(
            "price",
            0
        )

        text += (
            f"• {item_name} — "
            f"{item_price} ₽\n"
        )


    text += (
        f"\n💵 Итого: {total} ₽"
    )


    text += (
        "\n\n⚠️ Проверьте поступление "
        "денег перед выдачей товара."
    )


    # Получаем токен бота.

    bot_token = os.getenv(
        "BOT_TOKEN"
    )


    if not bot_token:

        return jsonify(
            error=(
                "BOT_TOKEN не настроен "
                "на Render"
            )
        ), 500


    # Получаем ВСЕХ администраторов,
    # включая владельца.

    conn = db()

    admin_rows = conn.execute(
        """
        SELECT telegram_id
        FROM admins
        """
    ).fetchall()

    conn.close()


    admin_ids = {
        int(row["telegram_id"])
        for row in admin_rows
    }


    # На всякий случай владелец
    # добавляется отдельно.

    admin_ids.add(
        OWNER_ID
    )


    sent = 0

    failed = []


    # Рассылаем сообщение
    # каждому администратору.

    for admin_id in admin_ids:

        try:

            response = requests.post(

                (
                    f"https://api.telegram.org/"
                    f"bot{bot_token}/sendMessage"
                ),

                json={
                    "chat_id":
                        admin_id,

                    "text":
                        text
                },

                timeout=10

            )


            if response.ok:

                sent += 1

            else:

                failed.append(
                    admin_id
                )


        except Exception:

            failed.append(
                admin_id
            )


    if sent == 0:

        return jsonify(
            error=(
                "Не удалось отправить "
                "уведомление ни одному "
                "администратору. "
                "Администраторы должны "
                "сначала нажать Start у бота."
            )
        ), 502


    return jsonify(
        ok=True,
        sent=sent,
        failed=failed
    )


# -------------------------
# ЗАПУСК
# -------------------------

init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        )
    )
