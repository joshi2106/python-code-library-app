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
