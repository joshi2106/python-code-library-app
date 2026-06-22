
from flask import Flask, jsonify
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


@app.route("/books", methods=["GET"])
def get_books():
    try:
        conn = get_db()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM books")

        books = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(books)

    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)


