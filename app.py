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
def save_feedback(item, feedback, rating, user_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute(
            "INSERT INTO feedbacks (item, feedback, rating, user_id) VALUES (?, ?, ?, ?)",
            (item, feedback, rating, user_id),
        )
    else:
        cur.execute(
            "INSERT INTO feedbacks (item, feedback, rating) VALUES (?, ?, ?)",
            (item, feedback, rating),
        )
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
    return pd.DataFrame(rows, columns=["item", "feedback", "rating", "timestamp"]) \
        if rows else pd.DataFrame(columns=["item", "feedback", "rating", "timestamp"])

# ----------------- SAVE RECEIPT -----------------
def save_receipt(order_id, items, total, payment_method, details="", user_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute(
            "INSERT INTO receipts (order_id, items, total, payment_method, details, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, items, total, payment_method, details, user_id),
        )
    else:
        cur.execute(
            "INSERT INTO receipts (order_id, items, total, payment_method, details) VALUES (?, ?, ?, ?, ?)",
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
    return pd.DataFrame(rows, columns=["items", "total", "payment_method", "timestamp"]) \
        if rows else pd.DataFrame(columns=["items", "total", "payment_method", "timestamp"])

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
                # Depending on Groq client version, adjust if needed
                answer = (
                    response.choices[0].message.content
                    if hasattr(response.choices[0], "message")
                    else response.choices[0].text
                )
                st.success(answer)
            except Exception as e:
                st.error(f"⚠️ AI unavailable: {e}")

st.divider()

# ---------- ORDER & FEEDBACK ----------
col1, col2 = st.columns(2)

# PLACE ORDER
with col1:
    st.subheader("🛒 Place an Order")

    if "cart" not in st.session_state:
        st.session_state.cart = {}

    for category, items in menu_data.items():
        with st.expander(category, expanded=False):
            for item, price in items.items():
                qty = st.number_input(f"{item} - ₱{price}", min_value=0, step=1, key=f"{category}_{item}")
                if qty > 0:
                    st.session_state.cart[item] = qty
                elif item in st.session_state.cart:
                    del st.session_state.cart[item]

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

# ---------- SALES REPORT ----------
st.subheader("📊 Sales Report")
sales_df = load_sales()

if not sales_df.empty:
    st.dataframe(sales_df)

    # map each item to its category
    item_to_category = {}
    for category, items in menu_data.items():
        for item in items.keys():
            item_to_category[item] = category

    # Expand "items" column into individual items
    expanded_rows = []
    for _, row in sales_df.iterrows():
        for entry in row["items"].split(","):
            entry = entry.strip()
            if "x" in entry:
                item, qty = entry.split("x")
                item = item.strip()
                qty = int(qty)
            else:
                item, qty = entry, 1
            expanded_rows.append({
                "item": item,
                "qty": qty,
                "total": row["total"],
                "payment_method": row["payment_method"],
                "timestamp": row["timestamp"],
                "category": item_to_category.get(item, "Other")
            })

    expanded_df = pd.DataFrame(expanded_rows)

    # 🔧 Ensure numeric for plotting
    expanded_df["total"] = pd.to_numeric(expanded_df["total"], errors="coerce")

    # Sales per category
    category_sales = expanded_df.groupby("category")["total"].sum()

    fig, ax = plt.subplots(figsize=(5,5))
    category_sales.plot(kind="bar", ax=ax)
    ax.set_ylabel("Total Sales (₱)")
    ax.set_title("Sales per Category")
    st.pyplot(fig)

else:
    st.info("No sales records available yet.")
