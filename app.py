from flask import Flask, render_template, request, redirect, session
import requests
import os

app = Flask(__name__)

# ================= BASIC CONFIG =================
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key_123")

# IMPORTANT:
# Must be False for localhost / testing
# Set True ONLY when running on HTTPS
app.config["SESSION_COOKIE_SECURE"] = False


# ================= OTP.DEV CONFIG =================
OTP_BASE_URL = "https://api.otp.dev/v1/verifications"

OTP_API_KEY  = os.getenv("OTP_API_KEY", "df2ea0a6b3e0a83be76ba95f55995fb8")
OTP_SENDER   = "faf6cb19-c47c-48b8-9b04-d29dc7a97ab2"
OTP_TEMPLATE = "28791c9e-10b3-4740-aa38-6273244335fc"


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
    mobile = request.form.get("mobile", "").strip()

    if not mobile.isdigit() or len(mobile) != 10:
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

    r = requests.post(OTP_BASE_URL, json=payload, headers=headers)

    print("SEND OTP STATUS:", r.status_code)
    print("SEND OTP RESPONSE:", r.text)

    if r.status_code in (200, 201):
        session["pending_mobile"] = mobile
        return render_template("verify.html", mobile=mobile)

    return "Failed to send OTP", 500


# ================= VERIFY OTP =================
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    mobile = request.form.get("mobile", "").strip()
    otp    = request.form.get("otp", "").strip()

    if not otp.isdigit():
        return "Invalid OTP format", 400

    if session.get("pending_mobile") != mobile:
        return "OTP expired. Request again.", 400

    params = {
        "code": otp,
        "phone": f"91{mobile}"
    }

    headers = {
        "X-OTP-Key": OTP_API_KEY,
        "accept": "application/json"
    }

    r = requests.get(OTP_BASE_URL, params=params, headers=headers)
    result = r.json()

    print("VERIFY STATUS:", r.status_code)
    print("VERIFY RESPONSE:", result)

    # otp.dev rule:
    # data array empty  => invalid OTP
    # data array filled => valid OTP
    if r.status_code == 200 and len(result.get("data", [])) > 0:
        session["user"] = mobile
        session.pop("pending_mobile", None)
        return redirect("/")

    return "Invalid OTP", 401


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
