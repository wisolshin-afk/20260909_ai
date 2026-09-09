import streamlit as st
import pandas as pd


st.set_page_config(page_title="구매 견적 계산기", layout="wide")
st.title("구매 견적 계산기")

if "items" not in st.session_state:
    st.session_state["items"] = []

if "editing_index" not in st.session_state:
    st.session_state["editing_index"] = None

if "editing_item" not in st.session_state:
    st.session_state["editing_item"] = None


def get_total_summary(items):
    df = pd.DataFrame(items)
    if df.empty:
        return 0, 0, 0

    subtotal = df["소계"].sum()
    vat = subtotal * 0.1
    total = subtotal + vat
    return subtotal, vat, total


editing_item = st.session_state.get("editing_item")

with st.form("quote_form"):
    st.subheader("품목 추가 / 수정")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        item_name = st.text_input(
            "품목명",
            value=editing_item["품목명"] if editing_item else "",
        )
    with col2:
        quantity = st.number_input(
            "수량",
            min_value=1,
            step=1,
            value=editing_item["수량"] if editing_item else 1,
        )
    with col3:
        unit_price = st.number_input(
            "단가",
            min_value=0,
            step=100,
            value=editing_item["단가"] if editing_item else 0,
        )
    with col4:
        st.write("")
        submit_label = "수정 완료" if st.session_state["editing_index"] is not None else "추가"
        submitted = st.form_submit_button(submit_label)

    if submitted:
        if item_name.strip() == "":
            st.warning("품목명을 입력해주세요.")
        else:
            item_total = quantity * unit_price
            new_item = {
                "품목명": item_name,
                "수량": quantity,
                "단가": unit_price,
                "소계": item_total,
            }

            if st.session_state["editing_index"] is not None:
                st.session_state["items"][st.session_state["editing_index"]] = new_item
                st.success(f"'{item_name}' 품목이 수정되었습니다.")
            else:
                st.session_state["items"].append(new_item)
                st.success(f"'{item_name}' 품목이 추가되었습니다.")

            st.session_state["editing_index"] = None
            st.session_state["editing_item"] = None

if st.session_state["items"]:
    df = pd.DataFrame(st.session_state["items"])
    st.subheader("견적 내역")
    st.dataframe(df, use_container_width=True, hide_index=True)

    subtotal, vat, total = get_total_summary(st.session_state["items"])

    st.subheader("총 견적 금액")
    col_sub, col_vat, col_total = st.columns(3)
    col_sub.metric("공급가액", f"{subtotal:,.0f}원")
    col_vat.metric("부가세(10%)", f"{vat:,.0f}원")
    col_total.metric("총 견적 금액", f"{total:,.0f}원")

    st.subheader("항목 관리")
    options = [f"{idx + 1}. {item['품목명']}" for idx, item in enumerate(st.session_state["items"])]
    selected_index = st.selectbox("수정 또는 삭제할 항목 선택", range(len(options)), format_func=lambda i: options[i])

    col_edit, col_delete = st.columns(2)
    with col_edit:
        if st.button("선택 항목 수정"):
            st.session_state["editing_index"] = selected_index
            st.session_state["editing_item"] = st.session_state["items"][selected_index].copy()
            st.rerun()

    with col_delete:
        if st.button("선택 항목 삭제"):
            del st.session_state["items"][selected_index]
            st.session_state["editing_index"] = None
            st.session_state["editing_item"] = None
            st.success("항목이 삭제되었습니다.")
            st.rerun()
else:
    st.info("품목을 추가하면 견적 내역이 표시됩니다.")

if st.session_state["items"]:
    if st.button("목록 초기화"):
        st.session_state["items"] = []
        st.session_state["editing_index"] = None
        st.session_state["editing_item"] = None
        st.rerun()

if st.session_state["editing_index"] is not None:
    st.info(f"현재 수정 중인 항목: {st.session_state['items'][st.session_state['editing_index']]['품목명']}")
