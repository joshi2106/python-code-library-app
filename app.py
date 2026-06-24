from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
import logging

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "library-secret-key")
logging.basicConfig(level=logging.INFO)

# ── Startup log — verify in CloudWatch immediately after deploy ────────────
_alb = os.getenv("ALB_URL", "NOT SET")
logging.info("=" * 50)
logging.info(f"ALB_URL at startup: {_alb}")
logging.info("=" * 50)
if _alb == "NOT SET":
    logging.error("CRITICAL: ALB_URL env var is missing — all service calls will fail!")


def get_service_urls():
    """
    Build service URLs at request time (not module load time).
    This ensures we always use the current ALB_URL value,
    even if the env var was slow to be injected by ECS.
    """
    base = os.getenv("ALB_URL", "").rstrip("/")
    return base, {
        "auth":   f"{base}/auth",
        "books":  f"{base}/books",
        "borrow": f"{base}/borrow",
    }


def call_service(method, url, **kwargs):
    """Centralised HTTP caller with consistent error handling."""
    try:
        res = getattr(requests, method)(url, timeout=10, **kwargs)
        logging.info(f"{method.upper()} {url} → {res.status_code}")
        return res
    except requests.exceptions.ConnectionError:
        logging.error(f"ConnectionError: cannot reach {url}")
        return None
    except requests.exceptions.Timeout:
        logging.error(f"Timeout: {url} did not respond in 10 s")
        return None
    except Exception as e:
        logging.error(f"Unexpected error calling {url}: {e}")
        return None


# ── HEALTH ─────────────────────────────────────────────────────────────────
# ALB frontend-tg health check path: /health

@app.route("/health")
def health():
    return {"status": "healthy"}, 200


# ── ROOT ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("books"))
    return redirect(url_for("signin"))


# ── AUTH ───────────────────────────────────────────────────────────────────
# /signup and /signup don't start with /auth /books /borrow → safe, stays in frontend

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        alb, urls = get_service_urls()
        if not alb:
            flash("Server misconfiguration: ALB_URL is not set.", "danger")
            return render_template("signup.html")

        data = {
            "name":     request.form.get("name"),
            "email":    request.form.get("email"),
            "password": request.form.get("password"),
        }
        # Internal call: POST ALB/auth/signup → ALB rule /auth* → auth_service
        res = call_service("post", f"{urls['auth']}/signup", json=data)

        if res is None:
            flash(f"Cannot reach auth service.", "danger")
        elif res.status_code == 201:
            flash("Account created! Please sign in.", "success")
            return redirect(url_for("signin"))
        elif res.status_code == 409:
            flash("Email already registered.", "warning")
        else:
            flash(res.json().get("error", "Signup failed."), "danger")

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        alb, urls = get_service_urls()
        if not alb:
            flash("Server misconfiguration: ALB_URL is not set.", "danger")
            return render_template("signin.html")

        data = {
            "email":    request.form.get("email"),
            "password": request.form.get("password"),
        }
        # Internal call: POST ALB/auth/signin → ALB rule /auth* → auth_service
        res = call_service("post", f"{urls['auth']}/signin", json=data)

        if res is None:
            flash(f"Cannot reach auth service.", "danger")
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


# ── BOOKS ──────────────────────────────────────────────────────────────────
#
# BUG FIX: route changed from /books to /library
#
# Why: ALB rule "/books*" intercepts ALL paths starting with /books —
# including the browser's GET /books intended for the frontend HTML page.
# The ALB would route it to book_service (which returns JSON), so the
# browser would see raw JSON instead of the rendered HTML page.
#
# Fix: browser hits /library (no ALB rule for it → stays in frontend).
# app.py internally calls ALB/books → book_service for JSON data.
# Update your HTML template hrefs from /books to /library accordingly.

@app.route("/library")
def books():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    _, urls = get_service_urls()
    # Internal call: GET ALB/books → ALB rule /books* → book_service GET /books
    res = call_service("get", urls["books"])

    if res is None:
        flash("Cannot reach book service.", "danger")
        return render_template("books.html", books=[])
    elif res.status_code == 200:
        return render_template("books.html", books=res.json())
    else:
        flash("Book service returned an error.", "danger")
        return render_template("books.html", books=[])


# ── BORROW ─────────────────────────────────────────────────────────────────
#
# BUG FIX: route changed from /borrow/<book_id> to /do-borrow/<book_id>
#
# Why: ALB rule "/borrow*" would intercept the browser's GET /borrow/<id>
# and send it to borrow_service which only accepts POST /borrow → 405 error.
#
# Fix: browser hits /do-borrow/<id> (no ALB rule → stays in frontend).
# app.py internally calls POST ALB/borrow → borrow_service.

@app.route("/do-borrow/<int:book_id>")
def borrow(book_id):
    if "user_id" not in session:
        return redirect(url_for("signin"))

    _, urls = get_service_urls()
    data = {"user_id": session["user_id"], "book_id": book_id}
    # Internal call: POST ALB/borrow → ALB rule /borrow* → borrow_service POST /borrow
    res  = call_service("post", urls["borrow"], json=data)

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

    _, urls = get_service_urls()
    # Internal call: GET ALB/borrow/mybooks/<id> → ALB rule /borrow* → borrow_service
    res = call_service("get", f"{urls['borrow']}/mybooks/{session['user_id']}")

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
