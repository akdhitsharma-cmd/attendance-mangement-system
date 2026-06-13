import streamlit as st
import mysql.connector
import datetime
import pandas as pd
import smtplib
import random
import os
import bcrypt
import cv2
import face_recognition
import numpy as np
import io

# ---------------- DATABASE ---------------- #
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="attendance_user",
        password="password123",
        database="attendance_db"
    )

# ---------------- EMAIL OTP ---------------- #
def send_otp(email):
    otp = str(random.randint(100000, 999999))

    sender = os.getenv("EMAIL_USER")
    app_password = os.getenv("EMAIL_PASS")

    message = f"Subject: OTP Verification\n\nYour OTP is {otp}"

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, app_password)
    server.sendmail(sender, email, message)
    server.quit()

    return otp

# ---------------- FACE CAPTURE ---------------- #
def capture_face():
    cap = cv2.VideoCapture(0)
    st.info("Press 'q' in camera window to capture")

    encoding = None

    while True:
        ret, frame = cap.read()
        cv2.imshow("Capture Face", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_encodings(rgb)

            if faces:
                encoding = faces[0]
            break

    cap.release()
    cv2.destroyAllWindows()
    return encoding

# ---------------- SLOT ---------------- #
def get_slot():
    hour = datetime.datetime.now().hour

    if 10 <= hour < 11:
        return "10-11 AM"
    elif 11 <= hour < 12:
        return "11-12 AM"
    elif 12 <= hour < 13:
        return "12-1 PM"
    elif 13 <= hour < 14:
        return "1-2 PM"
    else:
        return "Other"

# ---------------- UI ---------------- #
st.title("🎓 AI Attendance Management System")

menu = st.sidebar.selectbox("Menu", ["Register", "Login"])

# ---------------- REGISTER ---------------- #
if menu == "Register":
    st.subheader("Register User")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    email = st.text_input("Gmail")

    if st.button("Send OTP"):
        otp = send_otp(email)
        st.session_state["otp"] = otp
        st.success("OTP Sent ✅")

    user_otp = st.text_input("Enter OTP")

    if st.button("Capture Face"):
        face = capture_face()
        if face is not None:
            st.session_state["face"] = face.tolist()
            st.success("Face Captured ✅")
        else:
            st.error("Face not detected ❌")

    if st.button("Register"):

        if "otp" not in st.session_state:
            st.error("Generate OTP first ❌")

        elif user_otp != st.session_state.get("otp"):
            st.error("Invalid OTP ❌")

        elif "face" not in st.session_state:
            st.error("Capture face first ❌")

        else:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

            conn = connect_db()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "INSERT INTO users(username,password,email,face_encoding) VALUES(%s,%s,%s,%s)",
                    (username, hashed_pw.decode(), email, str(st.session_state["face"]))
                )
                conn.commit()
                st.success("Registration Successful ✅")

            except:
                st.error("Username already exists ❌")

            conn.close()

# ---------------- LOGIN ---------------- #
if menu == "Login":
    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_pw = result[0]

            if bcrypt.checkpw(password.encode(), stored_pw.encode()):
                st.session_state["user"] = username
                st.success("Login Successful ✅")
            else:
                st.error("Wrong Password ❌")
        else:
            st.error("User not found ❌")

    # -------- FACE LOGIN -------- #
    if st.button("Login with Face ID"):
        encoding = capture_face()

        if encoding is not None:
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("SELECT username, face_encoding FROM users")
            users = cursor.fetchall()
            conn.close()

            found = False

            for user, stored in users:
                stored_encoding = np.array(eval(stored))
                match = face_recognition.compare_faces([stored_encoding], encoding)

                if match[0]:
                    st.session_state["user"] = user
                    st.success(f"Welcome {user} (Face ID) ✅")
                    found = True
                    break

            if not found:
                st.error("Face not recognized ❌")

# ---------------- AFTER LOGIN ---------------- #
if "user" in st.session_state:
    st.subheader(f"Welcome {st.session_state['user']}")

    if st.button("Mark Attendance"):
        slot = get_slot()
        today = datetime.date.today()

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM attendance WHERE username=%s AND date=%s AND slot=%s",
            (st.session_state["user"], today, slot)
        )

        if cursor.fetchone():
            st.warning("Already Marked ⚠")
        else:
            cursor.execute(
                "INSERT INTO attendance(username,date,slot) VALUES(%s,%s,%s)",
                (st.session_state["user"], today, slot)
            )
            conn.commit()
            st.success(f"Attendance Marked ({slot}) ✅")

        conn.close()

    # -------- EXPORT -------- #
    if st.button("Export Attendance"):
        conn = connect_db()
        df = pd.read_sql("SELECT * FROM attendance", conn)
        conn.close()

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button(
            label="Download Excel",
            data=buffer,
            file_name="attendance.xlsx",
            mime="application/vnd.ms-excel"
        )