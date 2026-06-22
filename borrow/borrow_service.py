
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


@app.route("/borrow", methods=["POST"])
def borrow_book():
    try:
        data = request.json

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO borrow_records (user_id, book_id) VALUES (%s, %s)",
            (
                data["user_id"],
                data["book_id"]
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Book borrowed"}), 201

    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/mybooks/<int:user_id>", methods=["GET"])
def my_books(user_id):
    try:
        conn = get_db()

        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT b.title,
                   b.author,
                   br.borrow_date
            FROM borrow_records br
            JOIN books b
              ON br.book_id = b.id
            WHERE br.user_id = %s
            """,
            (user_id,)
        )

        books = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(books)

    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)

