from flask import Flask, render_template, request, redirect, session
import random
import time
import requests
import json

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# API Configuration
OTP_API_URL = "https://api.otp.dev/v1/verifications"
OTP_API_KEY = "df2ea0a6b3e0a83be76ba95f55995fb8"
OTP_SENDER = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
OTP_TEMPLATE = "28791c9e-10b3-4740-aa38-6273244335fc"

# Currency filter
def format_currency(amount):
    return "₹{:,.0f}".format(amount)

app.jinja_env.filters['currency'] = format_currency


@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/send-otp", methods=["POST"])
def send_otp():
    mobile = request.form["mobile"]

    if not mobile.isdigit() or len(mobile) != 10:
        return "Invalid mobile number"

    # Add 91 prefix for API
    phone_with_prefix = "91" + mobile

    try:
        payload = {
            "data": {
                "channel": "sms",
                "sender": OTP_SENDER,
                "phone": phone_with_prefix,
                "template": OTP_TEMPLATE,
                "code_length": 4
            }
        }
        
        headers = {
            "X-OTP-Key": OTP_API_KEY,
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(OTP_API_URL, json=payload, headers=headers)
        
        print(f"OTP Send Response: {response.status_code} - {response.text}")
        
        if response.status_code in [200, 201]:
             return render_template("verify.html", mobile=mobile)
        else:
             return f"Failed to send OTP: {response.text}"

    except Exception as e:
        return f"Error sending OTP: {str(e)}"


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.form["mobile"]
    entered_otp = request.form["otp"]
    
    # Add 91 prefix for API
    phone_with_prefix = "91" + mobile

    try:
        headers = {
            "X-OTP-Key": OTP_API_KEY,
            "accept": "application/json"
        }
        
        # Using GET method as per documentation found
        verify_url = f"{OTP_API_URL}?code={entered_otp}&phone={phone_with_prefix}"
        
        response = requests.get(verify_url, headers=headers)
        
        print(f"OTP Verify Response: {response.status_code} - {response.text}")

        # Check for success (usually 200 OK and data present)
        if response.status_code == 200:
            resp_json = response.json()
            # If 'data' is present and success is indicated (API specific, but usually 200 with data implies success)
            # The search result said "If the data field in the response is empty, it indicates that the code is invalid."
            if resp_json.get("data"): 
                session["user"] = mobile
                return redirect("/")
            else:
                 return "Invalid or expired OTP"
        else:
            return "Invalid OTP (API Error)"

    except Exception as e:
        return f"Error verifying OTP: {str(e)}"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


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
            hdfc_reason = "Strong profile match"
        else:
            loan_amount_hdfc = 0
            hdfc_reason = "Credit score below 700"

        results.append({
            "bank_name": "HDFC Bank",
            "amount": loan_amount_hdfc,
            "interest_rate": get_interest_rate('HDFC', loan_type, cibil_band),
            "color_theme": "#004c8f",
            "logo_text": "HDFC",
            "details": f"Based on 55% FOIR & 20x Multiplier. {hdfc_reason}."
        })

        # BoB
        if cibil_score >= 680:
            eligible_emi_bob = (income * 0.45) - existing_emis
            loan_amount_bob = max(eligible_emi_bob, 0) * 18
            bob_reason = "Standard eligibility criteria"
        else:
            loan_amount_bob = 0
            bob_reason = "Credit score below 680"

        results.append({
            "bank_name": "Bank of Baroda",
            "amount": loan_amount_bob,
            "interest_rate": get_interest_rate('BoB', loan_type, cibil_band),
            "color_theme": "#f26522",
            "logo_text": "BoB",
            "details": f"Based on 45% FOIR & 18x Multiplier. {bob_reason}."
        })

        return render_template('results.html', results=results, income=income)

    except Exception as e:
        return f"Error: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=False, port=8080, host='0.0.0.0', threaded=True)
