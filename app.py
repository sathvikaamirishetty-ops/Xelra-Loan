from flask import Flask, render_template, request, redirect, session
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "temporary_dev_key_123")
app.config["SESSION_COOKIE_SECURE"] = True

# ================= OTP CONFIG =================

OTP_BASE_URL = "https://api.otp.dev/v1/verifications"

OTP_API_KEY  = os.getenv("OTP_API_KEY", "df2ea0a6b3e0a83be76ba95f55995fb8")
OTP_SENDER   = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
OTP_TEMPLATE = "28791c9e-10b3-4740-aa38-6273244335fc"

# ================= FILTER =================

@app.template_filter('currency')
def format_currency(amount):
    try:
        return "₹{:,.0f}".format(float(amount))
    except:
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


# ================= SEND OTP =================

@app.route("/send-otp", methods=["POST"])
def send_otp():

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
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    try:
        r = requests.post(
            OTP_BASE_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

        data = r.json()

        print("======= OTP SEND =======")
        print("STATUS:", r.status_code)
        print("RESPONSE:", data)
        print("========================")

        if r.status_code in [200, 201] and data.get("data"):
            session["pending_mobile"] = mobile
            return render_template("verify.html", mobile=mobile)

        return f"OTP API Error: {data}", 500

    except Exception as e:
        return f"OTP Request Failed: {str(e)}", 500


# ================= VERIFY OTP =================

@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    mobile = request.form.get("mobile")
    otp = request.form.get("otp", "").strip()

    if not otp.isdigit():
        return "Invalid OTP", 400

    if session.get("pending_mobile") != mobile:
        return "Session expired. Request OTP again.", 400

    params = {
        "code": otp,
        "phone": f"91{mobile}"
    }

    headers = {
        "X-OTP-Key": OTP_API_KEY,
        "accept": "application/json"
    }

    try:
        r = requests.get(
            OTP_BASE_URL,
            params=params,
            headers=headers,
            timeout=15
        )

        result = r.json()

        print("======= OTP VERIFY =======")
        print("STATUS:", r.status_code)
        print("RESPONSE:", result)
        print("==========================")

        if r.status_code == 200 and len(result.get("data", [])) > 0:
            session["user"] = mobile
            session.pop("pending_mobile", None)
            return redirect("/")

        return f"Invalid OTP: {result}", 401

    except Exception as e:
        return f"Verify Failed: {str(e)}", 500


# ================= LOAN =================

@app.route('/calculate', methods=['POST'])
def calculate():

    if "user" not in session:
        return redirect("/login")

    try:
        income = float(request.form.get('income', 0))
        emis = float(request.form.get('existing_emis', 0))
    except:
        return "Invalid numbers", 400

    cibil = request.form.get('cibil_band')

    cibil_map = {
        "650": 600,
        "650–700": 675,
        "700–750": 725,
        "750+": 780
    }

    score = cibil_map.get(cibil, 700)

    hdfc = max((income * .55) - emis, 0) * 20 if score >= 700 else 0
    bob = max((income * .45) - emis, 0) * 18 if score >= 680 else 0

    results = [
        {
            "bank_name": "HDFC Bank",
            "amount": hdfc,
            "interest_rate": "8% – 12%",
            "color_theme": "#004c8f",
            "logo_text": "HDFC",
            "details": "Eligibility based on FOIR"
        },
        {
            "bank_name": "Bank of Baroda",
            "amount": bob,
            "interest_rate": "9% – 14%",
            "color_theme": "#f26522",
            "logo_text": "BoB",
            "details": "Standard criteria"
        }
    ]

    return render_template("results.html", results=results, income=income)


if __name__ == "__main__":
    app.run(debug=True)
