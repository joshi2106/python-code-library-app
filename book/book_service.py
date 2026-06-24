from flask import Flask, jsonify
import mysql.connector
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Startup log — verify DB env vars in CloudWatch immediately after deploy
logging.info("=" * 50)
logging.info(f"DB_HOST : {os.getenv('DB_HOST')}")
logging.info(f"DB_NAME : {os.getenv('DB_NAME')}")
logging.info(f"DB_USER : {os.getenv('DB_USER')}")
logging.info("=" * 50)


def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# ───────────────────────── HEALTH ─────────────────────────
# IMPORTANT: ALB Target Group health check path must be set to /book/health
@app.route("/books/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# ───────────────────────── GET ALL BOOKS ─────────────────────────
@app.route("/books", methods=["GET"])
def get_books():
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books ORDER BY id")
        books  = cursor.fetchall()
        cursor.close()
        conn.close()
        logging.info(f"Returned {len(books)} books")
        return jsonify(books), 200
    except Exception as e:
        logging.error(f"get_books error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ───────────────────────── GET SINGLE BOOK ─────────────────────────
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
        book   = cursor.fetchone()
        cursor.close()
        conn.close()
        if not book:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(book), 200
    except Exception as e:
        logging.error(f"get_book error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)

