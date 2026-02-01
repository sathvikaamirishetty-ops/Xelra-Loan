from flask import Flask, render_template, request, redirect, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "demo_secret")
app.config["SESSION_COOKIE_SECURE"] = True

# ================= OTP CONFIG =================

OTP_API_URL = "https://api.otp.dev/v1/verifications"
OTP_VERIFY_URL = "https://api.otp.dev/v1/verifications/verify"

OTP_API_KEY = "df2ea0a6b3e0a83be76ba95f55995fb8"
OTP_SENDER = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
OTP_TEMPLATE = "28791c9e-10b3-4740-aa38-6273244335fc"

# temp store (RAM)
verification_store = {}

# ================= FILTER =================

def format_currency(amount):
    return "₹{:,.0f}".format(amount)

app.jinja_env.filters['currency'] = format_currency


# ================= ROUTES =================

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


# ================= SEND OTP =================

@app.route("/send-otp", methods=["POST"])
def send_otp():

    mobile = request.form.get("mobile")

    if not mobile or not mobile.isdigit() or len(mobile) != 10:
        return "Invalid mobile"

    payload = {
        "data": {
            "channel": "sms",
            "sender": OTP_SENDER,
            "phone": f"91{mobile}",
            "template": OTP_TEMPLATE,
            "code_length": 4
        }
    }

    headers = {
        "X-OTP-Key": OTP_API_KEY,
        "content-type": "application/json"
    }

    r = requests.post(
        OTP_API_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    data = r.json()

    if "data" not in data:
        return "OTP failed"

    verification_store[mobile] = data["data"]["verification_id"]

    return render_template("verify.html", mobile=mobile)


# ================= VERIFY OTP =================

@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    mobile = request.form.get("mobile")
    otp = request.form.get("otp")

    verification_id = verification_store.get(mobile)

    if not verification_id:
        return "Session expired"

    payload = {
        "data": {
            "otp": otp,
            "verification_id": verification_id
        }
    }

    headers = {
        "X-OTP-Key": OTP_API_KEY,
        "content-type": "application/json"
    }

    r = requests.post(
        OTP_VERIFY_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    result = r.json()

    if result.get("data"):
        session["user"] = mobile
        verification_store.pop(mobile, None)
        return redirect("/")

    return "Invalid OTP"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= LOAN =================

@app.route('/calculate', methods=['POST'])
def calculate():

    if "user" not in session:
        return redirect("/login")

    income = float(request.form.get('income', 0))
    cibil = request.form.get('cibil_band')
    emis = float(request.form.get('existing_emis', 0))
    loan_type = request.form.get('loan_type')

    cibil_map = {
        "650": 600,
        "650–700": 675,
        "700–750": 725,
        "750+": 780
    }

    score = cibil_map.get(cibil, 700)

    results = []

    # HDFC
    hdfc = max((income * .55) - emis, 0) * 20 if score >= 700 else 0

    # BOB
    bob = max((income * .45) - emis, 0) * 18 if score >= 680 else 0

    results.append({
        "bank_name": "HDFC Bank",
        "amount": hdfc,
        "interest_rate": "8% – 12%",
        "color_theme": "#004c8f",
        "logo_text": "HDFC",
        "details": "Eligibility based on FOIR"
    })

    results.append({
        "bank_name": "Bank of Baroda",
        "amount": bob,
        "interest_rate": "9% – 14%",
        "color_theme": "#f26522",
        "logo_text": "BoB",
        "details": "Standard criteria"
    })

    return render_template("results.html", results=results, income=income)




