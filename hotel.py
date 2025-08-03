import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from datetime import datetime
import uuid

# -------------------- Firebase Init --------------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])  # ✅ Convert to dict
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred, {
        'storageBucket': f"{firebase_config['project_id']}.appspot.com"
    })

db = firestore.client()
bucket = storage.bucket()

# -------------------- Role Selection --------------------
role = st.sidebar.radio("Select Role", ["Admin", "Hotel Owner", "Customer"])

# -------------------- Admin Panel --------------------
if role == "Admin":
    st.title("Admin Dashboard")

    with st.form("add_hotel"):
        hotel_name = st.text_input("Hotel Name")
        description = st.text_area("Description")
        owner_email = st.text_input("Owner Email")
        owner_password = st.text_input("Owner Password", type="password")
        submitted = st.form_submit_button("Add Hotel")

        if submitted:
            # Create Hotel Owner Authentication
            user = auth.create_user(email=owner_email, password=owner_password)
            
            # Store hotel details
            db.collection("hotels").document(user.uid).set({
                "name": hotel_name,
                "description": description,
                "created_at": datetime.now()
            })
            st.success(f"Hotel '{hotel_name}' added successfully!")

    # View Orders Statistics
    st.subheader("Orders Statistics")
    orders = db.collection("orders").stream()
    for order in orders:
        data = order.to_dict()
        st.write(data)

# -------------------- Hotel Owner Panel --------------------
elif role == "Hotel Owner":
    st.title("Hotel Owner Dashboard")

    owner_email = st.text_input("Email")
    owner_id = st.text_input("Owner UID (from admin)")
    
    menu_tab, order_tab = st.tabs(["Add Menu", "Manage Orders"])

    with menu_tab:
        with st.form("add_menu"):
            menu_name = st.text_input("Menu Item")
            price = st.number_input("Price", min_value=0.0)
            image_file = st.file_uploader("Upload Image", type=["jpg", "png"])
            add_menu = st.form_submit_button("Add Menu")

            if add_menu:
                blob = bucket.blob(f"menu/{uuid.uuid4()}.jpg")
                blob.upload_from_file(image_file, content_type=image_file.type)
                img_url = blob.public_url

                db.collection("hotels").document(owner_id).collection("menu").add({
                    "name": menu_name,
                    "price": price,
                    "image": img_url,
                    "created_at": datetime.now()
                })
                st.success("Menu added successfully!")

    with order_tab:
        orders = db.collection("orders").where("hotel_id", "==", owner_id).stream()
        for order in orders:
            data = order.to_dict()
            st.write(data)
            if st.button(f"Confirm Order {order.id}"):
                db.collection("orders").document(order.id).update({"status": "confirmed"})
                st.success("Order Confirmed!")

# -------------------- Customer Panel --------------------
else:
    st.title("Customer Dashboard")

    with st.form("register"):
        name = st.text_input("Name")
        mobile = st.text_input("Mobile Number", max_chars=10)
        village = st.text_input("Village")
        address = st.text_area("Address")
        submit_reg = st.form_submit_button("Register")

        if submit_reg:
            customer_id = str(uuid.uuid4())
            db.collection("customers").document(customer_id).set({
                "name": name,
                "mobile": mobile,
                "village": village,
                "address": address,
                "created_at": datetime.now()
            })
            st.success("Registered successfully!")

    st.subheader("Browse Hotels")
    hotels = db.collection("hotels").stream()
    for hotel in hotels:
        data = hotel.to_dict()
        if st.button(f"View Menu - {data['name']}"):
            menus = db.collection("hotels").document(hotel.id).collection("menu").stream()
            for menu in menus:
                m = menu.to_dict()
                st.image(m["image"], width=100)
                st.write(f"{m['name']} - ₹{m['price']}")
                if st.button(f"Order {m['name']}"):
                    db.collection("orders").add({
                        "hotel_id": hotel.id,
                        "customer_mobile": mobile,
                        "item": m["name"],
                        "price": m["price"],
                        "status": "pending",
                        "created_at": datetime.now()
                    })
                    st.success("Order placed! Waiting for confirmation.")
