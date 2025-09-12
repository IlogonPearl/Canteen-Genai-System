import streamlit as st
import pandas as pd
import snowflake.connector
import uuid
import datetime

# ----------------- CONNECT -----------------
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        database=st.secrets["SNOWFLAKE_DATABASE"],
        schema=st.secrets["SNOWFLAKE_SCHEMA"],
    )

# ----------------- SAVE FEEDBACK -----------------
def save_feedback(item, feedback):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feedbacks (item, feedback) VALUES (%s, %s)", (item, feedback))
    conn.commit()
    cur.close()
    conn.close()

# ----------------- LOAD FEEDBACK -----------------
def load_feedbacks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT item, feedback, timestamp FROM feedbacks ORDER BY timestamp DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=["Item", "Feedback", "Timestamp"])

# ----------------- SAVE RECEIPT -----------------
def save_receipt(order_id, items, total, payment_method):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO receipts (order_id, items, total, payment_method) VALUES (%s, %s, %s, %s)",
        (order_id, items, total, payment_method)
    )
    conn.commit()
    cur.close()
    conn.close()

# ----------------- LOAD SALES -----------------
def load_sales():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT items, total, timestamp FROM receipts ORDER BY timestamp DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=["Items", "Total", "Timestamp"])


# ----------------- STREAMLIT UI -----------------
st.title("🍽️ Canteen Ordering System with Snowflake")

# --- Place Order ---
st.header("📌 Place an Order")
menu_items = ["Burger", "Fries", "Soda", "Pizza", "Pasta"]
selected_items = st.multiselect("Select items:", menu_items)
payment_method = st.selectbox("Payment Method", ["Cash", "Card", "E-Wallet"])

if st.button("Checkout"):
    if selected_items:
        order_id = str(uuid.uuid4())[:8]
        total = len(selected_items) * 50  # Dummy pricing
        save_receipt(order_id, ", ".join(selected_items), total, payment_method)
        st.success(f"✅ Order placed! ID: {order_id}, Total: ₱{total}")
    else:
        st.warning("Please select at least one item.")

# --- Feedback Section ---
st.header("💬 Give Feedback")
item_choice = st.selectbox("Which item?", menu_items)
feedback_text = st.text_area("Your feedback:")

if st.button("Submit Feedback"):
    if feedback_text.strip():
        save_feedback(item_choice, feedback_text)
        st.success("✅ Feedback saved to Snowflake!")
    else:
        st.warning("Please write something before submitting.")

# --- Show Feedbacks ---
st.subheader("📊 Feedback Records")
feedback_df = load_feedbacks()
st.dataframe(feedback_df)

# --- Sales Report ---
st.subheader("📈 Sales Report")
sales_df = load_sales()
st.dataframe(sales_df)
