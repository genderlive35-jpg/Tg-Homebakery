import os, sqlite3
from flask import Flask, request, jsonify, render_template, abort

app = Flask(__name__)
DB = "shop.db"

# ВАЖНО: перед запуском укажи свой Telegram ID.
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT DEFAULT '',
        image TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admins(
        telegram_id INTEGER PRIMARY KEY,
        owner INTEGER NOT NULL DEFAULT 0
    )""")
    if OWNER_ID:
        c.execute("INSERT OR REPLACE INTO admins(telegram_id,owner) VALUES(?,1)", (OWNER_ID,))
    c.commit(); c.close()

def tg_id():
    # Для первой версии ID передаётся из Telegram WebApp JS.
    # Перед публичным запуском нужно включить серверную проверку initData.
    try: return int(request.headers.get("X-Telegram-User-Id", "0"))
    except: return 0

def admin():
    uid=tg_id()
    c=db(); r=c.execute("SELECT owner FROM admins WHERE telegram_id=?", (uid,)).fetchone(); c.close()
    return r

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/admin")
def admin_page():
    return render_template("admin.html")

@app.get("/api/me")
def me():
    r=admin()
    return jsonify(id=tg_id(), admin=bool(r), owner=bool(r and r["owner"]))

@app.get("/api/products")
def products():
    c=db(); a=[dict(x) for x in c.execute("SELECT * FROM products ORDER BY id DESC")]; c.close()
    return jsonify(a)

@app.post("/api/products")
def add_product():
    if not admin(): abort(403)
    j=request.json or {}
    name=str(j.get("name","")).strip()
    if not name: return jsonify(error="Введите название"),400
    try: price=int(j.get("price",0))
    except: return jsonify(error="Неверная цена"),400
    c=db()
    c.execute("INSERT INTO products(name,price,description,image) VALUES(?,?,?,?)",
              (name,price,str(j.get("description","")),str(j.get("image",""))))
    c.commit(); c.close()
    return jsonify(ok=True)

@app.put("/api/products/<int:pid>")
def edit_product(pid):
    if not admin(): abort(403)
    j=request.json or {}
    c=db()
    c.execute("UPDATE products SET name=?,price=?,description=?,image=? WHERE id=?",
              (str(j.get("name","")),int(j.get("price",0)),str(j.get("description","")),str(j.get("image","")),pid))
    c.commit(); c.close()
    return jsonify(ok=True)

@app.delete("/api/products/<int:pid>")
def delete_product(pid):
    if not admin(): abort(403)
    c=db(); c.execute("DELETE FROM products WHERE id=?",(pid,)); c.commit(); c.close()
    return jsonify(ok=True)

@app.get("/api/admins")
def admins():
    r=admin()
    if not r or not r["owner"]: abort(403)
    c=db(); a=[dict(x) for x in c.execute("SELECT telegram_id,owner FROM admins ORDER BY owner DESC")]; c.close()
    return jsonify(a)

@app.post("/api/admins")
def add_admin():
    r=admin()
    if not r or not r["owner"]: abort(403)
    uid=int((request.json or {}).get("telegram_id",0))
    if not uid: return jsonify(error="Введите Telegram ID"),400
    c=db(); c.execute("INSERT OR IGNORE INTO admins(telegram_id,owner) VALUES(?,0)",(uid,)); c.commit(); c.close()
    return jsonify(ok=True)

@app.delete("/api/admins/<int:uid>")
def remove_admin(uid):
    r=admin()
    if not r or not r["owner"]: abort(403)
    c=db(); c.execute("DELETE FROM admins WHERE telegram_id=? AND owner=0",(uid,)); c.commit(); c.close()
    return jsonify(ok=True)

init_db()

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
