from flask import Flask, render_template, request, redirect, session, flash
import requests
import os

app = Flask(__name__)
# IMPORTANT: Use a real secret key in Vercel Environment Variables
app.secret_key = os.getenv("SECRET_KEY", "temporary_dev_key_123")
app.config["SESSION_COOKIE_SECURE"] = True

# ================= OTP CONFIG =================
OTP_API_URL = "https://api.otp.dev/v1/verifications"
OTP_VERIFY_URL = "https://api.otp.dev/v1/verifications/verify"

# It's better to put these in Vercel Environment Variables
OTP_API_KEY = os.getenv("OTP_API_KEY", "df2ea0a6b3e0a83be76ba95f55995fb8")
OTP_SENDER = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
OTP_TEMPLATE = "28791c9e-10b3-4740-aa38-6273244335fc"

# WARNING: This dict will clear frequently on Vercel because of Serverless restarts.

# ================= FILTER =================
@app.template_filter('currency')
def format_currency(amount):
    try:
        return "₹{:,.0f}".format(float(amount))
    except (ValueError, TypeError):
        return "₹0"

# ================= ROUTES =================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

# ================= SEND OTP (FIXED) =================
@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        mobile = request.form.get("mobile")

        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            return "Invalid mobile number", 400

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
            "Content-Type": "application/json"
        }

        r = requests.post(OTP_API_URL, json=payload, headers=headers, timeout=15)

        print("SEND STATUS:", r.status_code)
        print("SEND TEXT:", r.text)

        data = r.json()

        message_id = data.get("data", {}).get("message_id")

        if not message_id:
            return f"OTP API Failed: {data}", 500

        # ✅ Store in session (serverless safe)
        session["message_id"] = message_id
        session["mobile"] = mobile

        return render_template("verify.html", mobile=mobile)

    except Exception as e:
        print("SEND OTP ERROR:", str(e))
        return "Server error while sending OTP", 500

# ================= VERIFY OTP (FIXED) =================
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        otp = request.form.get("otp")
        mobile = session.get("mobile")
        message_id = session.get("message_id")

        if not otp or not message_id:
            return "Session expired. Try again.", 400

        payload = {
            "data": {
                "otp": otp,
                "message_id": message_id
            }
        }

        headers = {
            "X-OTP-Key": OTP_API_KEY,
            "Content-Type": "application/json"
        }

        r = requests.post(OTP_VERIFY_URL, json=payload, headers=headers, timeout=15)

        print("VERIFY STATUS:", r.status_code)
        print("VERIFY TEXT:", r.text)

        result = r.json()

        # ✅ OTP.dev returns: data.valid = true
        if result.get("data", {}).get("valid") == True:
            session.pop("message_id", None)
            session["user"] = mobile
            return redirect("/")

        return "Invalid OTP", 401

    except Exception as e:
        print("VERIFY ERROR:", str(e))
        return "Server error during verification", 500

# ================= LOAN =================
@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect("/login")

    try:
        income = float(request.form.get('income', 0))
        emis = float(request.form.get('existing_emis', 0))
    except ValueError:
        return "Please enter valid numbers for income and EMIs", 400

    cibil = request.form.get('cibil_band')
    
    cibil_map = {
        "650": 600,
        "650–700": 675,
        "700–750": 725,
        "750+": 780
    }

    score = cibil_map.get(cibil, 700)
    results = []

    # HDFC Calculation
    hdfc_amt = max((income * .55) - emis, 0) * 20 if score >= 700 else 0
    # BOB Calculation
    bob_amt = max((income * .45) - emis, 0) * 18 if score >= 680 else 0

    results.append({
        "bank_name": "HDFC Bank",
        "amount": hdfc_amt,
        "interest_rate": "8% – 12%",
        "color_theme": "#004c8f",
        "logo_text": "HDFC",
        "details": "Eligibility based on FOIR"
    })

    results.append({
        "bank_name": "Bank of Baroda",
        "amount": bob_amt,
        "interest_rate": "9% – 14%",
        "color_theme": "#f26522",
        "logo_text": "BoB",
        "details": "Standard criteria"
    })

    return render_template("results.html", results=results, income=income)

if __name__ == "__main__":
    app.run(debug=True)


