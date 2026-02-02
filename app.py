from flask import Flask, render_template, request, redirect, session
import requests
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# Currency filter
def format_currency(amount):
    try:
        return "₹{:,.0f}".format(float(amount))
    except:
        return "₹0"

app.jinja_env.filters['currency'] = format_currency

# OTP.dev configuration (USE ENV VARIABLES IN VERCEL)
OTP_API_KEY = os.environ.get("OTP_API_KEY")
SENDER_ID = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
TEMPLATE_ID = "28791c9e-10b3-4740-aa38-6273244335fc"


@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


# ---------------- SEND OTP ---------------- #

@app.route("/send-otp", methods=["POST"])
def send_otp():
    phone = request.form.get("phone")

    url = "https://api.otp.dev/v1/verifications"

    headers = {
        "X-OTP-Key": "YOUR_API_KEY",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "channel": "sms",
            "sender": "OTP",
            "recipient": phone
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        print("Status Code:", response.status_code)
        print("Raw Response:", response.text)  # 🔥 VERY IMPORTANT

        if response.status_code != 200:
            return f"API Error: {response.text}", 400

        try:
            data = response.json()
        except Exception:
            return f"Invalid JSON response: {response.text}", 400

        return "OTP Sent Successfully"

    except Exception as e:
        return f"Error: {str(e)}", 500


# ---------------- VERIFY OTP ---------------- #

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    entered_otp = request.form.get("otp")
    mobile = session.get("mobile")

    if not mobile:
        return "Session expired. Try again.", 400

    full_phone = "91" + mobile

    response = requests.post(
        "https://api.otp.dev/v1/verifications",
        headers={
            "X-OTP-Key": OTP_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json={
            "data": {
                "channel": "sms",
                "sender": SENDER_ID,          # REQUIRED
                "template": TEMPLATE_ID,      # REQUIRED
                "phone": full_phone,
                "code": entered_otp
            }
        }
    )

    result = response.json()

    if not response.ok:
        return f"Verification failed: {result}", 400

    session["user"] = mobile
    return redirect("/")




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- CALCULATOR ---------------- #

@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect("/login")

    try:
        income = float(request.form.get('income', 0))
        cibil_band = request.form.get('cibil_band')
        existing_emis = float(request.form.get('existing_emis', 0))
        loan_type = request.form.get('loan_type')

        cibil_map = {
            "<650": 600,
            "650–700": 675,
            "700–750": 725,
            "750+": 780
        }

        cibil_score = cibil_map.get(cibil_band, 700)
        results = []

        def get_interest_rate(bank, loan_type, cibil_band):
            if bank == 'HDFC':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.00% - 8.50%"
                    if cibil_band == '700–750': return "8.30% - 9.00%"
                    if cibil_band == '650–700': return "9.00% - 9.50%"
                    return "≥ 9.50%"
                else:
                    if cibil_band == '750+': return "10.00% - 12.00%"
                    if cibil_band == '700–750': return "12.00% - 15.00%"
                    if cibil_band == '650–700': return "15.00% - 18.00%"
                    return "18.00% - 24.00%"
            elif bank == 'BoB':
                if loan_type == 'Home':
                    if cibil_band == '750+': return "8.50% - 8.90%"
                    if cibil_band == '700–750': return "8.90% - 9.30%"
                    if cibil_band == '650–700': return "9.30% - 9.80%"
                    return "≥ 9.80%"
                else:
                    if cibil_band == '750+': return "12.00% - 14.00%"
                    if cibil_band == '700–750': return "14.00% - 17.00%"
                    if cibil_band == '650–700': return "17.00% - 20.00%"
                    return "≥ 20.00%"
            return "N/A"

        # HDFC
        if cibil_score >= 700:
            eligible_emi_hdfc = (income * 0.55) - existing_emis
            loan_amount_hdfc = max(eligible_emi_hdfc, 0) * 20
        else:
            loan_amount_hdfc = 0

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount_hdfc,
            "interest_rate": get_interest_rate('HDFC', loan_type, cibil_band),
            "color_theme": "#004c8f",
        })

        # BoB
        if cibil_score >= 680:
            eligible_emi_bob = (income * 0.45) - existing_emis
            loan_amount_bob = max(eligible_emi_bob, 0) * 18
        else:
            loan_amount_bob = 0

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount_bob,
            "interest_rate": get_interest_rate('BoB', loan_type, cibil_band),
            "color_theme": "#f26522",
        })

        return render_template('results.html', results=results, income=income)

    except Exception as e:
        return f"Error: {str(e)}", 400


