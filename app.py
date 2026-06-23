from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
import logging

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "library-secret-key")
logging.basicConfig(level=logging.INFO)

# ALB_URL must be set in ECS Task Definition environment variables
# Example: http://library-alb-409827736.us-east-1.elb.amazonaws.com
ALB_URL = os.getenv("ALB_URL", "").rstrip("/")

AUTH_URL  = f"{ALB_URL}/auth"
BOOK_URL  = f"{ALB_URL}/books"
BORROW_URL = f"{ALB_URL}/borrow"

# Log on startup so you can verify in CloudWatch immediately
logging.info(f"ALB_URL is set to: '{ALB_URL}'")
logging.info(f"AUTH_URL  -> {AUTH_URL}")
logging.info(f"BOOK_URL  -> {BOOK_URL}")
logging.info(f"BORROW_URL-> {BORROW_URL}")

if not ALB_URL:
    logging.error("CRITICAL: ALB_URL environment variable is not set!")


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
        if not ALB_URL:
            flash("Server misconfiguration: ALB_URL is not set", "danger")
            return render_template("signup.html")
        try:
            data = {
                "name": request.form["name"],
                "email": request.form["email"],
                "password": request.form["password"]
            }
            logging.info(f"Calling auth signup at: {AUTH_URL}/signup")
            res = requests.post(f"{AUTH_URL}/signup", json=data, timeout=10)
            logging.info(f"Auth signup response: {res.status_code} - {res.text}")

            if res.status_code == 201:
                flash("Account created! Please sign in.", "success")
                return redirect(url_for("signin"))
            else:
                # Show the actual error from auth service
                error_msg = res.json().get("error", "Signup failed")
                flash(error_msg, "danger")

        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error reaching auth service: {str(e)}")
            flash(f"Cannot reach auth service. Check ALB_URL config. ({ALB_URL})", "danger")
        except requests.exceptions.Timeout:
            logging.error("Auth service timed out")
            flash("Auth service timed out. Try again.", "danger")
        except Exception as e:
            logging.error(f"Unexpected signup error: {str(e)}")
            flash(f"Unexpected error: {str(e)}", "danger")

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        if not ALB_URL:
            flash("Server misconfiguration: ALB_URL is not set", "danger")
            return render_template("signin.html")
        try:
            data = {
                "email": request.form["email"],
                "password": request.form["password"]
            }
            logging.info(f"Calling auth signin at: {AUTH_URL}/signin")
            res = requests.post(f"{AUTH_URL}/signin", json=data, timeout=10)
            logging.info(f"Auth signin response: {res.status_code} - {res.text}")

            if res.status_code == 200:
                user = res.json()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                return redirect(url_for("books"))
            else:
                flash("Invalid email or password", "danger")

        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error reaching auth service: {str(e)}")
            flash(f"Cannot reach auth service. Check ALB_URL config. ({ALB_URL})", "danger")
        except requests.exceptions.Timeout:
            logging.error("Auth service timed out")
            flash("Auth service timed out. Try again.", "danger")
        except Exception as e:
            logging.error(f"Unexpected signin error: {str(e)}")
            flash(f"Unexpected error: {str(e)}", "danger")

    return render_template("signin.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("signin"))


# ---------------- BOOKS ----------------

@app.route("/books")
def books():
    if "user_id" not in session:
        return redirect(url_for("signin"))
    try:
        logging.info(f"Calling book service at: {BOOK_URL}")
        res = requests.get(f"{BOOK_URL}", timeout=10)
        logging.info(f"Book service response: {res.status_code}")
        return render_template("books.html", books=res.json())
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error reaching book service: {str(e)}")
        flash(f"Cannot reach book service. ({BOOK_URL})", "danger")
        return render_template("books.html", books=[])
    except Exception as e:
        logging.error(f"Book service error: {str(e)}")
        flash("Book service unavailable", "danger")
        return render_template("books.html", books=[])


# ---------------- BORROW ----------------

@app.route("/borrow/<int:book_id>")
def borrow(book_id):
    if "user_id" not in session:
        return redirect(url_for("signin"))
    try:
        data = {"user_id": session["user_id"], "book_id": book_id}
        logging.info(f"Calling borrow service at: {BORROW_URL}")
        res = requests.post(f"{BORROW_URL}", json=data, timeout=10)
        logging.info(f"Borrow service response: {res.status_code}")
        if res.status_code == 201:
            flash("Book borrowed successfully!", "success")
        else:
            flash(res.json().get("error", "Could not borrow book"), "danger")
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error reaching borrow service: {str(e)}")
        flash("Cannot reach borrow service", "danger")
    except Exception as e:
        logging.error(f"Borrow service error: {str(e)}")
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
        logging.error(f"Mybooks error: {str(e)}")
        flash("Borrow service unavailable", "danger")
        return render_template("borrow.html", books=[])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

