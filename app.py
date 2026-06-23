from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
import logging

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "library-secret-key")
logging.basicConfig(level=logging.INFO)

# ALB_URL is injected via ECS Task Definition environment variable
# Example: http://library-alb-409827736.us-east-1.elb.amazonaws.com
ALB_URL    = os.getenv("ALB_URL", "").rstrip("/")
AUTH_URL   = f"{ALB_URL}/auth"
BOOK_URL   = f"{ALB_URL}/books"
BORROW_URL = f"{ALB_URL}/borrow"

# Startup log — check CloudWatch immediately after deploy to verify ALB_URL is set
logging.info("=" * 50)
logging.info(f"ALB_URL    : {ALB_URL}")
logging.info(f"AUTH_URL   : {AUTH_URL}")
logging.info(f"BOOK_URL   : {BOOK_URL}")
logging.info(f"BORROW_URL : {BORROW_URL}")
logging.info("=" * 50)

if not ALB_URL:
    logging.error("CRITICAL: ALB_URL is not set in environment variables!")


# ───────────────────────── HELPERS ─────────────────────────

def call_service(method, url, **kwargs):
    """Centralised HTTP call with consistent error handling."""
    try:
        res = getattr(requests, method)(url, timeout=10, **kwargs)
        logging.info(f"{method.upper()} {url} → {res.status_code}")
        return res
    except requests.exceptions.ConnectionError:
        logging.error(f"ConnectionError: cannot reach {url}")
        return None
    except requests.exceptions.Timeout:
        logging.error(f"Timeout: {url} did not respond in 10s")
        return None
    except Exception as e:
        logging.error(f"Unexpected error calling {url}: {str(e)}")
        return None


# ───────────────────────── HEALTH ─────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200


# ───────────────────────── ROOT ─────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("books"))
    return redirect(url_for("signin"))


# ───────────────────────── AUTH ─────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if not ALB_URL:
            flash("Server misconfiguration: ALB_URL is not set. Check ECS Task Definition.", "danger")
            return render_template("signup.html")

        data = {
            "name":     request.form.get("name"),
            "email":    request.form.get("email"),
            "password": request.form.get("password")
        }

        res = call_service("post", f"{AUTH_URL}/signup", json=data)

        if res is None:
            flash(f"Cannot reach auth service. ALB_URL={ALB_URL}", "danger")
        elif res.status_code == 201:
            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for("signin"))
        elif res.status_code == 409:
            flash("Email already registered. Please sign in.", "warning")
        else:
            error = res.json().get("error", "Signup failed. Please try again.")
            flash(error, "danger")

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        if not ALB_URL:
            flash("Server misconfiguration: ALB_URL is not set. Check ECS Task Definition.", "danger")
            return render_template("signin.html")

        data = {
            "email":    request.form.get("email"),
            "password": request.form.get("password")
        }

        res = call_service("post", f"{AUTH_URL}/signin", json=data)

        if res is None:
            flash(f"Cannot reach auth service. ALB_URL={ALB_URL}", "danger")
        elif res.status_code == 200:
            user = res.json()
            session["user_id"] = user["user_id"]
            session["name"]    = user["name"]
            return redirect(url_for("books"))
        elif res.status_code == 401:
            flash("Invalid email or password.", "danger")
        else:
            flash("Sign in failed. Please try again.", "danger")

    return render_template("signin.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("signin"))


# ───────────────────────── BOOKS ─────────────────────────

@app.route("/books")
def books():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    res = call_service("get", f"{BOOK_URL}")

    if res is None:
        flash(f"Cannot reach book service. ALB_URL={ALB_URL}", "danger")
        return render_template("books.html", books=[])
    elif res.status_code == 200:
        return render_template("books.html", books=res.json())
    else:
        flash("Book service returned an error.", "danger")
        return render_template("books.html", books=[])


# ───────────────────────── BORROW ─────────────────────────

@app.route("/borrow/<int:book_id>")
def borrow(book_id):
    if "user_id" not in session:
        return redirect(url_for("signin"))

    data = {
        "user_id": session["user_id"],
        "book_id": book_id
    }

    res = call_service("post", f"{BORROW_URL}", json=data)

    if res is None:
        flash("Cannot reach borrow service.", "danger")
    elif res.status_code == 201:
        flash("Book borrowed successfully!", "success")
    elif res.status_code == 409:
        flash("You have already borrowed this book.", "warning")
    elif res.status_code == 404:
        flash("Book not found.", "danger")
    else:
        flash("Could not borrow book. Please try again.", "danger")

    return redirect(url_for("books"))


@app.route("/mybooks")
def mybooks():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    res = call_service("get", f"{BORROW_URL}/mybooks/{session['user_id']}")

    if res is None:
        flash("Cannot reach borrow service.", "danger")
        return render_template("borrow.html", books=[])
    elif res.status_code == 200:
        return render_template("borrow.html", books=res.json())
    else:
        flash("Could not fetch your books.", "danger")
        return render_template("borrow.html", books=[])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
