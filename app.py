from flask import Flask, render_template, request, redirect, session
import random
import time

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

# In-memory store for OTPs
otp_store = {}

def generate_otp():
    return random.randint(1000, 9999)

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

    otp = generate_otp()
    expiry = time.time() + 300

    otp_store[mobile] = {
        "otp": otp,
        "expiry": expiry,
        "attempts": 0
    }

    # SIMULATION: Print OTP to console AND write to file
    print(f"\n{'='*30}\nSIMULATED SMS to {mobile}: Your OTP is {otp}\n{'='*30}\n")
    
    # Missing return statement in provided snippet added back to maintain flow
    return render_template("verify.html", mobile=mobile)


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.form["mobile"]
    entered_otp = request.form["otp"]

    data = otp_store.get(mobile)

    if not data:
        return "OTP not found"

    if time.time() > data["expiry"]:
        del otp_store[mobile]
        return "OTP expired"

    if str(data["otp"]) == entered_otp:
        session["user"] = mobile
        del otp_store[mobile]
        return redirect("/")
    else:
        return "Invalid OTP"


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


