import csv
from datetime import datetime
from pathlib import Path

import streamlit as st


DATA_FILE = Path(__file__).with_name("customers.csv")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def load_customers():
    """파일에서 고객 데이터를 읽어와 리스트로 반환한다."""
    if not DATA_FILE.exists():
        return []

    rows = []
    with DATA_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append(
                {
                    "customer_id": int(row.get("customer_id", 0) or 0),
                    "name": row.get("name", ""),
                    "email": row.get("email", ""),
                    "phone": row.get("phone", ""),
                    "address": row.get("address", ""),
                    "join_date": row.get("join_date", ""),
                }
            )
    return rows


def save_customers(customers):
    """고객 데이터를 파일에 저장한다."""
    fieldnames = [
        "customer_id",
        "name",
        "email",
        "phone",
        "address",
        "join_date",
    ]
    with DATA_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(customers)


def get_next_customer_id(customers):
    """다음 고객 ID를 계산한다."""
    if not customers:
        return 1
    return max(int(c["customer_id"]) for c in customers) + 1


def login_form():
    """관리자 로그인 폼을 출력한다."""
    st.sidebar.subheader("관리자 로그인")
    username = st.sidebar.text_input("아이디", key="login_username")
    password = st.sidebar.text_input("비밀번호", type="password", key="login_password")

    if st.sidebar.button("로그인"):
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state["logged_in"] = True
            st.session_state["admin_name"] = username
            st.sidebar.success("로그인 성공")
        else:
            st.sidebar.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    if st.session_state.get("logged_in"):
        st.sidebar.success(f"관리자: {st.session_state.get('admin_name')}")
        if st.sidebar.button("로그아웃"):
            st.session_state["logged_in"] = False
            st.session_state.pop("admin_name", None)
            st.rerun()


def show_customer_list(customers):
    """고객 목록을 표시한다."""
    st.subheader("고객 목록")

    if not customers:
        st.info("등록된 고객이 없습니다.")
        return

    st.dataframe(
        [
            {
                "고객ID": c["customer_id"],
                "이름": c["name"],
                "이메일": c["email"],
                "전화번호": c["phone"],
                "주소": c["address"],
                "가입일자": c["join_date"],
            }
            for c in customers
        ],
        use_container_width=True,
    )


def add_or_update_customer(customers):
    """고객 추가 / 수정 폼을 관리한다."""
    st.subheader("고객 등록 / 수정")

    with st.form("customer_form"):
        customer_id = st.number_input("고객ID", min_value=1, step=1, value=get_next_customer_id(customers))
        name = st.text_input("이름")
        email = st.text_input("이메일")
        phone = st.text_input("전화번호")
        address = st.text_area("주소")
        join_date = st.date_input("가입일자", value=datetime.today().date())

        submitted = st.form_submit_button("저장")
        if submitted:
            if not name or not email or not phone:
                st.warning("이름, 이메일, 전화번호는 필수 입력 항목입니다.")
                return

            existing_index = next(
                (i for i, c in enumerate(customers) if c["customer_id"] == customer_id),
                None,
            )

            new_customer = {
                "customer_id": int(customer_id),
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "join_date": join_date.isoformat(),
            }

            if existing_index is not None:
                customers[existing_index] = new_customer
                st.success("고객 정보가 수정되었습니다.")
            else:
                customers.append(new_customer)
                st.success("새 고객이 등록되었습니다.")

            save_customers(customers)
            st.rerun()


def delete_customer(customers):
    """고객 삭제 기능."""
    st.subheader("고객 삭제")
    selected_id = st.selectbox("삭제할 고객 선택", [c["customer_id"] for c in customers])
    if st.button("삭제"):
        customers[:] = [c for c in customers if c["customer_id"] != selected_id]
        save_customers(customers)
        st.success("고객이 삭제되었습니다.")
        st.rerun()


def app():
    st.set_page_config(page_title="와이솔 쇼핑몰 고객관리", layout="wide")
    st.title("와이솔 쇼핑몰 고객 관리 시스템")
    st.caption("AI 용품 쇼핑몰 관리자용 고객 정보 관리 페이지")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    login_form()

    if not st.session_state.get("logged_in"):
        st.warning("관리자 로그인이 필요합니다.")
        return

    customers = load_customers()

    tab1, tab2, tab3 = st.tabs(["고객 목록", "고객 등록/수정", "고객 삭제"])

    with tab1:
        show_customer_list(customers)

    with tab2:
        add_or_update_customer(customers)

    with tab3:
        delete_customer(customers)


if __name__ == "__main__":
    app()
