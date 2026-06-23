from flask import Flask, request, jsonify, redirect, url_for
import mysql.connector
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.route("/auth/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/auth/signup", methods=["POST"])
def signup():
    try:
        # Handle both HTML form submissions AND JSON (Postman/API calls)
        if request.is_json:
            data = request.json
        else:
            data = request.form

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "name, email and password are required"}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            return jsonify({"error": "Email already registered"}), 409

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        logging.info(f"New user registered: {email}")

        # If request came from a browser form, redirect to signin page
        if not request.is_json:
            return redirect("/signin?registered=true")

        return jsonify({"message": "User created successfully"}), 201

    except Exception as e:
        logging.error(f"Signup error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/auth/signin", methods=["POST"])
def signin():
    try:
        # Handle both HTML form submissions AND JSON (Postman/API calls)
        if request.is_json:
            data = request.json
        else:
            data = request.form

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            logging.info(f"User signed in: {email}")

            # If request came from a browser form, redirect to books page
            if not request.is_json:
                return redirect("/books")

            return jsonify({
                "message": "Login successful",
                "user_id": user["id"],
                "name": user["name"]
            }), 200

        return jsonify({"message": "Invalid credentials"}), 401

    except Exception as e:
        logging.error(f"Signin error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)


