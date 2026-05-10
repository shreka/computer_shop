import csv
import json
import os
from datetime import datetime
import requests

from flask import Flask, flash, redirect, render_template, request, session, url_for


folder = os.path.dirname(os.path.abspath(__file__))

products_file = os.path.join(folder, "products.json")
users_file = os.path.join(folder, "users.json")
stock_file = os.path.join(folder, "stock.csv")
login_file = os.path.join(folder, "login_log.csv")

app = Flask(
    __name__,
    template_folder=os.path.join(folder, "templates"),
    static_folder=os.path.join(folder, "static"),
)
app.secret_key = "skolasprojekts2025"


def read_json(file_name):
    with open(file_name, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


products = read_json(products_file)["products"]
users = read_json(users_file)["users"]


def read_stock():
    stock = {}

    with open(stock_file, "r", encoding="utf-8", newline="") as file:
        rows = csv.DictReader(file)
        for row in rows:
            product_id = int(row["product_id"])
            stock[product_id] = {
                "quantity": int(row["quantity"]),
                "warehouse": row["warehouse"],
            }

    return stock


def products_with_stock():
    stock = read_stock()
    product_list = []

    for product in products:
        one_product = product.copy()
        one_product["stock"] = stock.get(
            product["id"], {"quantity": 0, "warehouse": "Nav zināms"}
        )
        product_list.append(one_product)

    return product_list


def find_product(product_id):
    for product in products_with_stock():
        if product["id"] == product_id:
            return product
    return None


def log_login(username, success):
    file_exists = os.path.exists(login_file)

    with open(login_file, "a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)

        if not file_exists or os.path.getsize(login_file) == 0:
            writer.writerow(["timestamp", "username", "success"])

        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([time_now, username, success])


def get_stock(symbol):

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

        stock_time = datetime.fromtimestamp(int(data["t"])).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return {
            "symbol": symbol,
            "price": round(float(data["c"]), 2),
            "change_percent": round(float(data.get("dp", 0)), 2),
            "time": stock_time,
        }
    except (requests.RequestException, ValueError, KeyError):
        return {"error": True}


@app.route("/")
def index():
    return render_template("index.html", products=products_with_stock())


@app.route("/product/<int:id>")
def product_detail(id):
    product = find_product(id)

    if product is None:
        flash("Produkts netika atrasts")
        return redirect(url_for("index"))

    return render_template("product.html", product=product)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        success = False

        for user in users:
            if user["username"] == username and user["password"] == password:
                success = True

        log_login(username, success)

        if success:
            session["user"] = username
            flash("Laipni lūdzam!")
            return redirect(url_for("index"))

        flash("Nepareizs lietotājvārds vai parole")

    return render_template("login.html")


@app.route("/stocks")
def stocks():
    stock_data = [get_stock("NVDA"), get_stock("AMD")]

    for item in stock_data:
        if item.get("error"):
            stock_data = None

    return render_template("stocks.html", stock_data=stock_data)


@app.route("/category/<name>")
def category(name):
    shown_products = products_with_stock()

    if name.lower() != "all":
        shown_products = [
            product
            for product in shown_products
            if product["category"].lower() == name.lower()
        ]

    return render_template(
        "index.html",
        products=shown_products,
        category=name,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
