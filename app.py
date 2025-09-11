import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import qrcode
import uuid
import os
from groq import Groq   # ✅ GenAI client

# ================================
# SETUP
# ================================
st.set_page_config(page_title="🍔 School Canteen GenAI", layout="wide")
st.markdown("Welcome in our Canteen Genai, Please Enjoy our Service")
client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# ================================
# MENU DATA
# ================================
menu_data = {
    "Breakfast": {"Pancakes": 30, "Omelette": 25, "Toast": 15},
    "Snack": {"Burger": 50, "Spaghetti": 60, "Fries": 40, "Pizza": 250},
    "Lunch": {"Rice": 10, "Fried Egg": 20, "Chicken Curry": 70, "Fried Chicken": 50, "Hotdog": 35},
    "Drinks": {"Coke": 20, "Iced Tea": 25, "Bottled Water": 15, "Coffee": 20, "Milk Tea": 45},
    "Dessert": {"Ice Cream": 30, "Cupcake": 25, "Leche Flan": 35},
}

# ================================
# SESSION STATES
# ================================
if "orders" not in st.session_state:
    st.session_state.orders = []

if "feedback" not in st.session_state:
    st.session_state.feedback = []

if "receipts" not in st.session_state:
    st.session_state.receipts = []

# ================================
# LAYOUT
# ================================
col1, col2 = st.columns([1, 2])

# ================================
# LEFT SIDE → MENU + CART + CHECKOUT
# ================================
with col1:
    st.header("🔍 Search Menu")

    filter_category = st.text_input("Enter category (Breakfast, Snack, Lunch, Drinks, Dessert):").capitalize()
    if filter_category in menu_data:
        st.subheader(f"{filter_category} Menu")
        for item, price in menu_data[filter_category].items():
            if st.button(f"Add {item} - ₱{price}"):
                st.session_state.orders.append(item)
                st.success(f"{item} added to order ✅")

    st.subheader("🛒 Your Order")
    if st.session_state.orders:
        order_counts = Counter(st.session_state.orders)
        total = 0
        for item, count in order_counts.items():
            price = None
            for category in menu_data.values():
                if item in category:
                    price = category[item]
            if price:
                st.write(f"{item} x{count} = ₱{price * count}")
                total += price * count

        st.write(f"### 💵 Total = ₱{total}")

        # Remove item
        remove_item = st.selectbox("Select item to remove:", [""] + list(order_counts.keys()))
        if st.button("Remove Item") and remove_item:
            st.session_state.orders.remove(remove_item)
            st.warning(f"{remove_item} removed from order ❌")

        # Replace item
        replace_item = st.selectbox("Select item to replace:", [""] + list(order_counts.keys()))
        new_item = st.selectbox("Replace with:", [""] + [i for c in menu_data.values() for i in c])
        if st.button("Replace Item") and replace_item and new_item:
            idx = st.session_state.orders.index(replace_item)
            st.session_state.orders[idx] = new_item
            st.info(f"{replace_item} replaced with {new_item} 🔄")

        # Checkout
        st.subheader("💳 Checkout")
        payment_method = st.radio("Choose Payment Method:", ["Cash", "Online"])

        if st.button("Proceed to Payment"):
            order_id = str(uuid.uuid4())[:8]
            receipt_text = f"Order ID: {order_id}\nItems: {st.session_state.orders}\nTotal: ₱{total}\nPayment: {payment_method}"

            if payment_method == "Cash":
                qr = qrcode.make(receipt_text)
                qr_path = f"receipt_{order_id}.png"
                qr.save(qr_path)
                st.image(qr_path, caption="📷 Show this QR at the counter")
            else:
                st.success("✅ Payment completed online!")
                st.text(receipt_text)

            # Save receipt
            st.session_state.receipts.append({
                "order_id": order_id,
                "items": ", ".join(st.session_state.orders),
                "total": total,
                "payment_method": payment_method,
            })
            pd.DataFrame(st.session_state.receipts).to_csv("receipts.csv", index=False)
            st.success("📄 Receipt generated and saved!")

    else:
        st.info("No items ordered yet.")

# ================================
# RIGHT SIDE → GENAI + FEEDBACK + REPORTS
# ================================
with col2:
    # GenAI Assistant
    st.header("🤖 Ask Canteen AI")
    user_input = st.text_input("Type your question:")
    if st.button("Ask AI"):
        if user_input:
            menu_text = ", ".join(
                [f"{item} ({price})" for cat in menu_data.values() for item, price in cat.items()]
            )
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",   # ✅ Groq model
                    messages=[
                        {"role": "system", "content": f"You are a friendly canteen assistant. The menu includes: {menu_text}. Suggest combos, budget-friendly meals, or answer naturally."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.write("*AI:*", response.choices[0].message.content)
            except Exception as e:
                st.error(f"⚠️ AI model error: {e}")

    # Feedback
    st.subheader("💬 Give Feedback")
    feedback_text = st.text_area("What do you think about the canteen system?")
    if st.button("Submit Feedback"):
        if feedback_text:
            st.session_state.feedback.append(feedback_text)
            pd.DataFrame(st.session_state.feedback, columns=["feedback"]).to_csv("feedback.csv", index=False)
            st.success("✅ Feedback recorded, thank you!")

    if st.session_state.feedback:
        st.write("### 📜 Previous Feedback (Anonymous)")
        for fb in st.session_state.feedback[-5:]:  # show last 5
            st.info(f"💭 {fb}")

    # Most Bought Items
    st.subheader("📊 Most Bought Items")
    if st.session_state.orders:
        order_counts = Counter(st.session_state.orders)
        df = pd.DataFrame(order_counts.items(), columns=["Item", "Count"])

        fig, ax = plt.subplots()
        ax.bar(df["Item"], df["Count"])
        ax.set_xlabel("Menu Item")
        ax.set_ylabel("Times Ordered")
        ax.set_title("Most Popular Menu Items")
        st.pyplot(fig)
    else:
        st.info("No orders yet to display chart.")

    # Sales Report
    st.subheader("📈 Sales Report")
    if os.path.exists("receipts.csv"):
        all_receipts = pd.read_csv("receipts.csv")
        report = all_receipts.groupby("items")["total"].sum().reset_index()

        fig2, ax2 = plt.subplots()
        ax2.bar(report["items"], report["total"])
        ax2.set_xlabel("Menu Item")
        ax2.set_ylabel("Total Sales (₱)")
        ax2.set_title("Sales Report by Item")
        st.pyplot(fig2)
    else:

        st.info("No sales recorded yet.")
