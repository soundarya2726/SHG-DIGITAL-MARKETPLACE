from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "shg_secret_key"


def create_database():
    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL
        )
    """)

    # Add user_id to old products table if it does not already exist
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]

    if "user_id" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
    """)

    products = cursor.fetchall()

    conn.close()

    return render_template("index.html", products=products)


# Register
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("shg.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )

        conn.commit()
        conn.close()

        flash("Registration Successful! Please Login.")
        return redirect("/login")

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("shg.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            # Store logged-in user details
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]

            flash("Login Successful!")
            return redirect("/dashboard")

        else:
            flash("Invalid Email or Password!")
            return redirect("/login")

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
        WHERE user_id = ?
    """, (user_id,))

    products = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        products=products
    )


# Add Product
@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if "user_id" not in session:
        flash("Please login to add products.")
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]

        user_id = session["user_id"]

        conn = sqlite3.connect("shg.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products
            (name, description, price, user_id)
            VALUES (?, ?, ?, ?)
        """, (name, description, price, user_id))

        conn.commit()
        conn.close()

        flash("Product Added Successfully!")
        return redirect("/dashboard")

    return render_template("add_product.html")

# Edit Product
@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
        WHERE id = ? AND user_id = ?
    """, (product_id, session["user_id"]))

    product = cursor.fetchone()

    if not product:
        conn.close()
        flash("Product not found!")
        return redirect("/dashboard")

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]

        try:
            price = float(price)
            if price < 0:
                raise ValueError

            cursor.execute("""
                UPDATE products
                SET name = ?, description = ?, price = ?
                WHERE id = ? AND user_id = ?
            """, (
                name,
                description,
                price,
                product_id,
                session["user_id"]
            ))

            conn.commit()
            conn.close()

            flash("Product Updated Successfully!")
            return redirect("/dashboard")

        except ValueError:
            flash("Please enter a valid price.")
            conn.close()
            return redirect(f"/edit-product/{product_id}")

    conn.close()
    return render_template("edit_product.html", product=product)





# Logout
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!")
    return redirect("/")

# Buy Product
@app.route("/buy/<int:product_id>")
def buy_product(product_id):

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
        WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    conn.close()

    if product:
        return render_template("buy.html", product=product)

    flash("Product not found!")
    return redirect("/")

# Place Order
@app.route("/place-order/<int:product_id>", methods=["GET", "POST"])
def place_order(product_id):

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
        WHERE id = ?
    """, (product_id,))

    product = cursor.fetchone()

    if not product:
        conn.close()
        flash("Product not found!")
        return redirect("/")

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        phone = request.form["phone"]
        address = request.form["address"]

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT DEFAULT 'Pending'
            )
        """)

        cursor.execute("""
            INSERT INTO orders
            (product_id, customer_name, phone, address)
            VALUES (?, ?, ?, ?)
        """, (product_id, customer_name, phone, address))

        conn.commit()
        conn.close()

        flash("Order placed successfully! 🎉")
        return redirect("/")

    conn.close()

    return render_template("order.html", product=product)

# Seller Orders
@app.route("/orders")
def orders():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            orders.id,
            products.name,
            orders.customer_name,
            orders.phone,
            orders.address,
            orders.status
        FROM orders
        JOIN products
        ON orders.product_id = products.id
        WHERE products.user_id = ?
    """, (session["user_id"],))

    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html", orders=orders)

@app.route("/update-order/<int:order_id>", methods=["POST"])
def update_order(order_id):
    if "user_id" not in session:
        return redirect("/login")

    status = request.form["status"]

    if status not in ["Pending", "Confirmed", "Delivered"]:
        flash("Invalid order status!")
        return redirect("/orders")

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
        AND product_id IN (
            SELECT id FROM products WHERE user_id = ?
        )
    """, (status, order_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("Order status updated successfully!")
    return redirect("/orders")



@app.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("shg.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM products
        WHERE id = ? AND user_id = ?
    """, (product_id, user_id))

    conn.commit()
    conn.close()

    flash("Product deleted successfully!")
    return redirect("/dashboard")

create_database()

if __name__ == "__main__":
    app.run(debug=True)


