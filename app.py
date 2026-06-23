from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
import logging

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "library-secret-key")

logging.basicConfig(level=logging.INFO)

ALB_URL = os.getenv("ALB_URL")
AUTH_URL = f"{ALB_URL}/auth"
BOOK_URL = f"{ALB_URL}/books"
BORROW_URL = f"{ALB_URL}/borrow"

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("books"))
    return redirect(url_for("signin"))

# ---------------- AUTH ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            data = {
                "name": request.form["name"],
                "email": request.form["email"],
                "password": request.form["password"]
            }
            res = requests.post(f"{AUTH_URL}/signup", json=data, timeout=10)
            if res.status_code == 201:
                flash("Signup successful!", "success")
                return redirect(url_for("signin"))
            flash("Signup failed", "danger")
        except Exception as e:
            logging.error(str(e))
            flash("Service unavailable", "danger")
    return render_template("signup.html")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        try:
            data = {
                "email": request.form["email"],
                "password": request.form["password"]
            }
            res = requests.post(f"{AUTH_URL}/signin", json=data, timeout=10)
            if res.status_code == 200:
                user = res.json()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                return redirect(url_for("books"))
            flash("Invalid credentials", "danger")
        except Exception as e:
            logging.error(str(e))
            flash("Authentication service unavailable", "danger")
    return render_template("signin.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("signin"))

# ---------------- BOOKS ----------------
@app.route("/books")
def books():
    if "user_id" not in session:
        return redirect(url_for("signin"))
    try:
        res = requests.get(f"{BOOK_URL}", timeout=10)
        return render_template("books.html", books=res.json())
    except Exception as e:
        logging.error(str(e))
        flash("Book service unavailable", "danger")
        return render_template("books.html", books=[])

# ---------------- BORROW ----------------
@app.route("/borrow/<int:book_id>")
def borrow(book_id):
    if "user_id" not in session:
        return redirect(url_for("signin"))
    try:
        data = {"user_id": session["user_id"], "book_id": book_id}
        res = requests.post(f"{BORROW_URL}", json=data, timeout=10)
        if res.status_code == 201:
            flash("Book borrowed!", "success")
    except Exception as e:
        logging.error(str(e))
        flash("Borrow service unavailable", "danger")
    return redirect(url_for("books"))

@app.route("/mybooks")
def mybooks():
    if "user_id" not in session:
        return redirect(url_for("signin"))
    try:
        res = requests.get(f"{BORROW_URL}/mybooks/{session['user_id']}", timeout=10)
        return render_template("borrow.html", books=res.json())
    except Exception as e:
        logging.error(str(e))
        flash("Borrow service unavailable", "danger")
        return render_template("borrow.html", books=[])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
