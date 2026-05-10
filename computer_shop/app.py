import csv
import json
import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
STOCK_FILE = os.path.join(BASE_DIR, "stock.csv")
LOGIN_LOG_FILE = os.path.join(BASE_DIR, "login_log.csv")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = "skolasprojekts2025"


def load_json_file(path):
    """Nolasa JSON failu un atgriež Python vārdnīcu."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


PRODUCTS = load_json_file(PRODUCTS_FILE)["products"]
USERS = load_json_file(USERS_FILE)["users"]


def load_stock_data():
    """Nolasa produktu krājumu no CSV faila."""
    stock_by_product = {}
    with open(STOCK_FILE, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            product_id = int(row["product_id"])
            stock_by_product[product_id] = {
                "quantity": int(row["quantity"]),
                "warehouse": row["warehouse"],
            }
    return stock_by_product


def get_products_with_stock():
    """Apvieno produktu JSON datus ar CSV krājumu datiem."""
    stock_data = load_stock_data()
    products = []
    for product in PRODUCTS:
        product_copy = product.copy()
        product_copy["stock"] = stock_data.get(
            product["id"], {"quantity": 0, "warehouse": "Nav zināms"}
        )
        products.append(product_copy)
    return products


def get_product_by_id(product_id):
    for product in get_products_with_stock():
        if product["id"] == product_id:
            return product
    return None


def write_login_attempt(username, success):
    """Pieraksta katru pieteikšanās mēģinājumu CSV žurnālā."""
    file_exists = os.path.exists(LOGIN_LOG_FILE)
    with open(LOGIN_LOG_FILE, "a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        if not file_exists or os.path.getsize(LOGIN_LOG_FILE) == 0:
            writer.writerow(["timestamp", "username", "success"])
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                success,
            ]
        )


def fetch_stock_quote(symbol):
    """Iegūst akciju cenu no Finnhub API."""
    try:
        import requests
    except ImportError:
        return {"error": True}

    api_key = os.getenv("FINNHUB_API_KEY", "d80bvr1r01qq9ln3agi0d80bvr1r01qq9ln3agig")

    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": api_key},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()

        if not data or data.get("c") in (None, 0) or data.get("t") in (None, 0):
            return {"error": True}

        return {
            "symbol": symbol,
            "price": round(float(data["c"]), 2),
            "change_percent": round(float(data.get("dp", 0)), 2),
            "time": datetime.fromtimestamp(int(data["t"])).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
    except (requests.RequestException, ValueError, KeyError):
        return {"error": True}


@app.route("/")
def index():
    products = get_products_with_stock()
    return render_template("index.html", products=products)


@app.route("/product/<int:id>")
def product_detail(id):
    product = get_product_by_id(id)
    if product is None:
        flash("Produkts netika atrasts")
        return redirect(url_for("index"))
    return render_template("product.html", product=product)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        success = any(
            user["username"] == username and user["password"] == password
            for user in USERS
        )
        write_login_attempt(username, success)

        if success:
            session["user"] = username
            flash("Laipni lūdzam!")
            return redirect(url_for("index"))

        flash("Nepareizs lietotājvārds vai parole")

    return render_template("login.html")


@app.route("/stocks")
def stocks():
    quotes = [fetch_stock_quote("NVDA"), fetch_stock_quote("AMD")]
    stock_data = None if any(item.get("error") for item in quotes) else quotes
    return render_template("stocks.html", stock_data=stock_data)


@app.route("/category/<name>")
def category(name):
    products = get_products_with_stock()
    if name.lower() != "all":
        products = [
            product
            for product in products
            if product["category"].lower() == name.lower()
        ]
    return render_template("index.html", products=products, category=name)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
