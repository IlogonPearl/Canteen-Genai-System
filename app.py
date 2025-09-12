import streamlit as st
import pandas as pd
import snowflake.connector
from groq import Groq
import random
from datetime import datetime
import matplotlib.pyplot as plt

# ----------------- CONNECT TO SNOWFLAKE -----------------
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
    return pd.DataFrame(rows, columns=["Item", "Feedback", "Timestamp"]) if rows else pd.DataFrame(columns=["Item", "Feedback", "Timestamp"])

# ----------------- SAVE RECEIPT -----------------
def save_receipt(order_id, items, total, payment_method):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO receipts (order_id, items, total, payment_method) VALUES (%s, %s, %s, %s)",
        (order_id, items, total, payment_method),
    )
    conn.commit()
    cur.close()
    conn.close()

# ----------------- LOAD SALES -----------------
def load_sales():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT items, total, timestamp FROM receipts")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=["Items", "Total", "Timestamp"]) if rows else pd.DataFrame(columns=["Items", "Total", "Timestamp"])

# ----------------- MENU DATA -----------------
menu_data = {
    "Burger": 50,
    "Fries": 30,
    "Soda": 20,
    "Spaghetti": 45,
    "Chicken Meal": 80,
    "Siomai Rice": 60,
}

# ----------------- AI CLIENT -----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ----------------- UI -----------------
st.set_page_config(page_title="Canteen GenAI System", layout="wide")
st.title("🏫 Canteen GenAI System")

# ---------- AI ASSISTANT ----------
st.markdown("### 🤖 Canteen AI Assistant")

col_left, col_mid, col_right = st.columns([1, 2, 1])
with col_mid:
    user_query = st.text_input("Ask me about menu, budget, feedback, or sales:")
    if st.button("Ask AI"):
        if user_query:
            sales_df = load_sales()
            feedback_df = load_feedbacks()

            context = f"""
            MENU:
            {menu_data}

            SALES DATA:
            {sales_df.to_dict() if not sales_df.empty else "No sales"}

            FEEDBACK DATA:
            {feedback_df.to_dict() if not feedback_df.empty else "No feedback"}
            """

            prompt = f"""
            You are a smart AI assistant for a school canteen.
            - Suggest combo meals with prices when asked.
            - Answer budget questions (e.g. meals under ₱100).
            - Summarize sales and most popular items.
            - Share product feedback if requested.
            Be concise and helpful.

            Context:
            {context}

            Question:
            {user_query}
            """

            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                )
                st.success(response.choices[0].message.content)
            except Exception as e:
                st.error(f"⚠️ AI unavailable: {e}")

st.divider()

# ---------- ORDER & FEEDBACK ----------
col1, col2 = st.columns(2)

# PLACE ORDER
with col1:
    st.subheader("🛒 Place an Order")
    selected_items = st.multiselect("Choose items:", list(menu_data.keys()))
    total = sum(menu_data[item] for item in selected_items)
    payment_method = st.radio("Payment Method", ["Cash", "Card", "E-Wallet"])
    if st.button("Place Order"):
        if selected_items:
            order_id = f"ORD{random.randint(1000,9999)}"
            save_receipt(order_id, ", ".join(selected_items), total, payment_method)
            st.success(f"✅ Order placed! Order ID: {order_id} | Total: ₱{total}")
        else:
            st.warning("Please select at least one item.")

# GIVE FEEDBACK
with col2:
    st.subheader("✍️ Give Feedback")
    feedback_item = st.selectbox("Select Item:", list(menu_data.keys()))
    feedback_text = st.text_area("Your Feedback:")
    if st.button("Submit Feedback"):
        if feedback_text:
            save_feedback(feedback_item, feedback_text)
            st.success("✅ Feedback submitted!")
        else:
            st.warning("Please write feedback before submitting.")

# ---------- FEEDBACK RECORDS ----------
st.subheader("📝 Feedback Records")
feedback_df = load_feedbacks()
if not feedback_df.empty:
    st.dataframe(feedback_df)
else:
    st.info("No feedback available yet.")

# ---------- SALES REPORT ----------
st.subheader("📊 Sales Report")
sales_df = load_sales()
if not sales_df.empty:
    st.dataframe(sales_df)

    # Bar chart for sales
    sales_summary = sales_df.groupby("Items")["Total"].sum()
    fig, ax = plt.subplots()
    sales_summary.plot(kind="bar", ax=ax)
    ax.set_ylabel("Total Sales (₱)")
    ax.set_title("Sales per Item")
    st.pyplot(fig)
else:
    st.info("No sales records available yet.")

