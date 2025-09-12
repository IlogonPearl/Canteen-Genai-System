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
def save_feedback(item, feedback, rating):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feedbacks (item, feedback, rating) VALUES (%s, %s, %s)", (item, feedback, rating))
    conn.commit()
    cur.close()
    conn.close()

# ----------------- LOAD FEEDBACK -----------------
def load_feedbacks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT item, feedback, rating, timestamp FROM feedbacks ORDER BY timestamp DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=["Item", "Feedback", "Rating", "Timestamp"]) if rows else pd.DataFrame(columns=["Item", "Feedback", "Rating", "Timestamp"])

# ----------------- SAVE RECEIPT -----------------
def save_receipt(order_id, items, total, payment_method, details=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO receipts (order_id, items, total, payment_method, details) VALUES (%s, %s, %s, %s, %s)",
        (order_id, items, total, payment_method, details),
    )
    conn.commit()
    cur.close()
    conn.close()

# ----------------- LOAD SALES -----------------
def load_sales():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT items, total, payment_method, timestamp FROM receipts")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=["Items", "Total", "Payment Method", "Timestamp"]) if rows else pd.DataFrame(columns=["Items", "Total", "Payment Method", "Timestamp"])

# ----------------- MENU DATA -----------------
menu_data = {
    "Breakfast": {"Tapsilog": 70, "Longsilog": 65, "Hotdog Meal": 50, "Omelette": 45},
    "Lunch": {"Chicken Adobo": 90, "Pork Sinigang": 100, "Beef Caldereta": 120, "Rice": 15},
    "Snack": {"Burger": 50, "Fries": 30, "Siomai Rice": 60, "Spaghetti": 45},
    "Drinks": {"Soda": 20, "Iced Tea": 25, "Bottled Water": 15, "Coffee": 30},
    "Dessert": {"Halo-Halo": 65, "Leche Flan": 40, "Ice Cream": 35},
    "Dinner": {"Grilled Chicken": 95, "Sisig": 110, "Fried Bangus": 85, "Rice": 15},
}

# ----------------- AI CLIENT -----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ----------------- UI -----------------
st.set_page_config(page_title="Canteen GenAI System", layout="wide")
st.title("🏫 Canteen GenAI System")

# ---------- AI ASSISTANT ----------
st.markdown("### 🤖 Canteen AI Assistant")

col_left, col_mid, col_right = st.columns([1, 2, 1])
with col_left:
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

    # session state for cart
    if "cart" not in st.session_state:
        st.session_state.cart = {}

    # expandable categories
    for category, items in menu_data.items():
        with st.expander(category, expanded=False):
            for item, price in items.items():
                qty = st.number_input(f"{item} - ₱{price}", min_value=0, step=1, key=f"{category}_{item}")
                if qty > 0:
                    st.session_state.cart[item] = qty
                elif item in st.session_state.cart:
                    del st.session_state.cart[item]

    # show cart
    if st.session_state.cart:
        st.markdown("#### 🛒 Your Cart")
        total = 0
        for item, qty in st.session_state.cart.items():
            price = None
            for cat, items in menu_data.items():
                if item in items:
                    price = items[item]
            subtotal = price * qty
            total += subtotal
            st.write(f"{item} x {qty} = ₱{subtotal}")

        st.write(f"**Total: ₱{total}**")

        # payment method
        payment_method = st.radio("Payment Method", ["Cash", "Card", "E-Wallet"])

        payment_details = ""
        if payment_method == "Card":
            card_num = st.text_input("Card Number")
            expiry = st.text_input("Expiry Date (MM/YY)")
            cvv = st.text_input("CVV", type="password")
            payment_details = f"Card: {card_num}, Exp: {expiry}"
        elif payment_method == "E-Wallet":
            wallet_type = st.selectbox("Choose Wallet", ["GCash", "Maya", "QR Scan"])
            payment_details = wallet_type

        if st.button("Place Order"):
            order_id = f"ORD{random.randint(1000,9999)}"
            items_str = ", ".join([f"{k}x{v}" for k,v in st.session_state.cart.items()])
            save_receipt(order_id, items_str, total, payment_method, payment_details)
            st.success(f"✅ Order placed! Order ID: {order_id} | Total: ₱{total}")
            st.session_state.cart = {}

# GIVE FEEDBACK
with col2:
    st.subheader("✍️ Give Feedback")
    feedback_item = st.selectbox("Select Item:", [i for cat in menu_data.values() for i in cat.keys()])
    rating = st.slider("Rate this item (1-5 stars):", 1, 5, 3)
    feedback_text = st.text_area("Your Feedback:")
    if st.button("Submit Feedback"):
        if feedback_text:
            save_feedback(feedback_item, feedback_text, rating)
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

# ----------------- SALES REPORT -----------------
st.subheader("📈 Sales Report by Category")

sales = load_sales()
if sales:
    sales_df = pd.DataFrame(sales, columns=["items", "total", "timestamp"])

    # Map each item to its category
    item_to_category = {
        item: cat
        for cat, items in menu_data.items()
        for item in items.keys()
    }

    sales_df["Category"] = sales_df["items"].map(item_to_category)

    # Group sales by category
    category_sales = sales_df.groupby("Category")["total"].sum().reset_index()

    # Plot smaller graph
    fig, ax = plt.subplots(figsize=(4,2))  # compact graph
    ax.bar(category_sales["Category"], category_sales["total"])
    ax.set_xlabel("Category")
    ax.set_ylabel("Total Sales (₱)")
    ax.set_title("Sales by Category")
    st.pyplot(fig, use_container_width=False)
else:
    st.info("No sales recorded yet.")




