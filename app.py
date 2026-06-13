import streamlit as st
import mysql.connector
import datetime
import pandas as pd
import smtplib
import random

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="attendance_user",
        password="password123",
        database="attendance_db"
    )
def send_otp(email):
    otp = str(random.randint(100000, 999999))

    sender = "akshitsharma578@gmail.com"
    app_password = "vguvfbocgbqhtezp"

    message = f"Subject: OTP Verification\n\nYour OTP is {otp}"

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login(sender, app_password)
    server.sendmail(sender, email, message)
    server.quit()

    return otp

def get_slot():
    now = datetime.datetime.now()
    hour = now.hour

    if 10 <= hour < 11:
        return "10-11 AM"
    elif 11 <= hour < 12:
        return "11-12 PM"
    elif 12 <= hour < 13:
        return "12-1 PM"
    elif 13 <= hour < 14:
        return "1-2 PM"
    else:
        return "Other"

st.title("Attendance Management System")

menu = st.sidebar.selectbox("Menu", ["Register", "Login"])

if menu == "Register":

    st.subheader("Register User")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    email = st.text_input("Gmail")

    if st.button("Send OTP"):
        otp = send_otp(email)
        st.session_state["otp"] = otp
        st.success("OTP Sent to Gmail ✅")

    user_otp = st.text_input("Enter OTP")

    if st.button("Register"):
        if user_otp == st.session_state.get("otp"):

            conn = connect_db()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "INSERT INTO users(username,password,email) VALUES(%s,%s,%s)",
                    (username, password, email)
                )
                conn.commit()
                st.success("Registration Successful ✅")

            except:
                st.error("Username Already Exists ❌")

            conn.close()

        else:
            st.error("Invalid OTP ❌")

if menu == "Login":

    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            st.session_state["user"] = username
            st.success("Login Successful ✅")
        else:
            st.error("Invalid Credentials ❌")

if "user" in st.session_state:

    st.subheader(f"Welcome {st.session_state['user']}")

    if st.button("Mark Attendance"):

        slot = get_slot()
        today = datetime.date.today()

        conn = connect_db()
        cursor = conn.cursor()

        # Prevent duplicate entry
        cursor.execute(
            "SELECT * FROM attendance WHERE username=%s AND date=%s AND slot=%s",
            (st.session_state["user"], today, slot)
        )

        already = cursor.fetchone()

        if already:
            st.warning("Attendance Already Marked For This Slot ⚠")
        else:
            cursor.execute(
                "INSERT INTO attendance(username,date,slot) VALUES(%s,%s,%s)",
                (st.session_state["user"], today, slot)
            )
            conn.commit()
            st.success(f"Attendance Marked For {slot} ✅")

        conn.close()

    if st.button("Export Attendance To Excel"):
        conn = connect_db()
        df = pd.read_sql("SELECT * FROM attendance", conn)
        conn.close()

        df.to_excel("attendance.xlsx", index=False)
        st.success("Exported to attendance.xlsx ✅")
