import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, storage, auth
from datetime import datetime
import uuid

# -------------------- Firebase Init --------------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)

    firebase_admin.initialize_app(cred, {
        'databaseURL': f"https://{firebase_config['project_id']}.firebaseio.com",
        'storageBucket': f"{firebase_config['project_id']}.appspot.com"
    })

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

            # Store hotel details in Realtime DB
            ref = db.reference("hotels")
            ref.child(user.uid).set({
                "name": hotel_name,
                "description": description,
                "created_at": datetime.now().isoformat()
            })
            st.success(f"Hotel '{hotel_name}' added successfully!")

    # View Orders Statistics
    st.subheader("Orders Statistics")
    orders_ref = db.reference("orders").get()
    if orders_ref:
        for order_id, data in orders_ref.items():
            st.write(f"Order ID: {order_id}", data)

# -------------------- Hotel Owner Panel --------------------
elif role == "Hotel Owner":
    st.title("Hotel Owner Dashboard")

    owner_id = st.text_input("Owner UID (from admin)")
    menu_tab, order_tab = st.tabs(["Add Menu", "Manage Orders"])

    with menu_tab:
        with st.form("add_menu"):
            menu_name = st.text_input("Menu Item")
            price = st.number_input("Price", min_value=0.0)
            image_file = st.file_uploader("Upload Image", type=["jpg", "png"])
            add_menu = st.form_submit_button("Add Menu")

            if add_menu:
                if not owner_id:
                    st.error("Please enter your Owner UID")
                else:
                    blob = bucket.blob(f"menu/{uuid.uuid4()}.jpg")
                    blob.upload_from_file(image_file, content_type=image_file.type)
                    img_url = blob.public_url

                    db.reference(f"hotels/{owner_id}/menu").push({
                        "name": menu_name,
                        "price": price,
                        "image": img_url,
                        "created_at": datetime.now().isoformat()
                    })
                    st.success("Menu added successfully!")

    with order_tab:
        orders = db.reference("orders").order_by_child("hotel_id").equal_to(owner_id).get()
        if orders:
            for order_id, data in orders.items():
                st.write(data)
                if st.button(f"Confirm Order {order_id}"):
                    db.reference(f"orders/{order_id}/status").set("confirmed")
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
            db.reference(f"customers/{customer_id}").set({
                "name": name,
                "mobile": mobile,
                "village": village,
                "address": address,
                "created_at": datetime.now().isoformat()
            })
            st.success("Registered successfully!")

    st.subheader("Browse Hotels")
    hotels = db.reference("hotels").get()
    if hotels:
        for hotel_id, data in hotels.items():
            st.write(f"🏨 {data['name']} - {data['description']}")
            if st.button(f"View Menu - {data['name']}", key=hotel_id):
                menus = db.reference(f"hotels/{hotel_id}/menu").get()
                if menus:
                    for menu_id, m in menus.items():
                        st.image(m["image"], width=100)
                        st.write(f"{m['name']} - ₹{m['price']}")
                        if st.button(f"Order {m['name']}", key=menu_id):
                            order_id = db.reference("orders").push({
                                "hotel_id": hotel_id,
                                "customer_mobile": mobile,
                                "item": m["name"],
                                "price": m["price"],
                                "status": "pending",
                                "created_at": datetime.now().isoformat()
                            }).key
                            st.success(f"Order {order_id} placed! Waiting for confirmation.")
