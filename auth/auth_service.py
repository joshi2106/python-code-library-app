from flask import Flask, request, jsonify
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

@app.route("/health", methods=["GET"])
def health():
return jsonify({"status": "healthy"}), 200

@app.route("/signup", methods=["POST"])
def signup():
try:
data = request.json

```
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
        (data["name"], data["email"], data["password"])
    )

    conn.commit()

    cursor.close()
    conn.close()

    logging.info("User created successfully")

    return jsonify({"message": "User created"}), 201

except Exception as e:
    logging.error(str(e))
    return jsonify({"error": str(e)}), 500
```

@app.route("/signin", methods=["POST"])
def signin():
try:
data = request.json

```
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (data["email"], data["password"])
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify({
            "message": "Login success",
            "user_id": user["id"],
            "name": user["name"]
        })

    return jsonify({"message": "Invalid credentials"}), 401

except Exception as e:
    logging.error(str(e))
    return jsonify({"error": str(e)}), 500
```

if **name** == "**main**":
app.run(host="0.0.0.0", port=5001)

