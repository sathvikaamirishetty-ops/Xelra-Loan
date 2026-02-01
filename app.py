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
    mobile = request.form.get("mobile")

    if not mobile or not mobile.isdigit() or len(mobile) != 10:
        return "Invalid mobile number. Must be 10 digits.", 400

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

    r = requests.post(OTP_API_URL, json=payload, headers=headers)
    data = r.json()

    print("FULL OTP RESPONSE:", data)

    if r.status_code in [200, 201]:

        message_id = data.get("data", {}).get("message_id")

        if not message_id:
            return f"No message_id found: {data}", 500

        # ✅ FIX 2: Store message_id in session instead of in-memory dict
        # This survives Vercel serverless restarts
        session["pending_message_id"] = message_id
        session["pending_mobile"] = mobile

        return render_template("verify.html", mobile=mobile)

    return f"OTP API Error: {data}", 500

# ================= VERIFY OTP (FIXED) =================
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.form.get("mobile")
    otp = request.form.get("otp", "").strip()

    print(f"Received mobile: {mobile}, OTP: {otp}")

    if not otp or not otp.isdigit():
        return "Invalid OTP format. Enter numbers only.", 400

    message_id = session.get("pending_message_id")
    session_mobile = session.get("pending_mobile")

    print(f"Session message_id: {message_id}, Session mobile: {session_mobile}")

    if not message_id or session_mobile != mobile:
        return f"OTP expired. Session mobile: {session_mobile}, Input mobile: {mobile}", 400

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

    print("SENDING VERIFY PAYLOAD:", payload)
    print("HEADERS:", headers)

    try:
        r = requests.post(OTP_VERIFY_URL, json=payload, headers=headers)
        result = r.json()

        print("VERIFY RESPONSE:", result)
        print("STATUS CODE:", r.status_code)
        print("RESPONSE HEADERS:", dict(r.headers))

        if r.status_code in [200, 201]:
            data = result.get("data", {})
            
            # Try multiple ways to check verification
            if (data.get("status") == "verified" or 
                data.get("verified") == True or 
                result.get("status") == "verified" or
                result.get("verified") == True):
                
                session["user"] = mobile
                session.pop("pending_message_id", None)
                session.pop("pending_mobile", None)
                return redirect("/")

        return f"Verification failed. Status: {r.status_code}, Response: {result}", 401

    except Exception as e:
        print("ERROR:", str(e))
        return f"Network error: {str(e)}", 500


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


