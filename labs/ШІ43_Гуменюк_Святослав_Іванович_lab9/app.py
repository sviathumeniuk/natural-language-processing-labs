import groq
import streamlit as st

from agent import run_agent


def show_final_answer(final_answer: dict) -> None:
    st.subheader("Відповідь Радника")
    st.success(final_answer["answer_text"])
    st.markdown("**Знамення, на які він спирається:**")

    for fact in final_answer["key_facts"]:
        st.markdown(f"- {fact}")


def show_trace(trace: list[dict]) -> None:
    with st.expander(f"Виклики інструментів ({len(trace)})"):
        if not trace:
            st.write("Агент не викликав жодного інструмента.")

        for tool_call in trace:
            st.markdown(f"**{tool_call['tool']}**")
            st.json({"arguments": tool_call["arguments"], "result": tool_call["result"]}, expanded=False)


st.set_page_config(page_title="Радник")
st.title("Радник")
st.markdown(
    "**Радник** — потужна космічно логічна система, що здатна передбачати "
    "найтонші події світу."
)
st.markdown(
    "Запитайте його про майбутнє: він зважить знамення з десятка джерел "
    "і дасть відповідь, яку можна перевірити."
)
st.caption(
    "Для роботи потрібен ключ Groq. "
)

api_key = st.text_input("Groq API ключ", type="password", placeholder="gsk_...").strip()
question = st.text_area("Ваше питання про майбутнє").strip()
city = st.text_input("Ваше місто", placeholder="Наприклад, Таллінн").strip()

if st.button("Запитати Радника", type="primary"):
    if not api_key:
        st.error("Вкажіть Groq API ключ.")
    elif not question:
        st.error("Введіть питання.")
    elif not city:
        st.error("Введіть місто: воно потрібне для погоди та місцевого часу.")
    else:
        try:
            with st.spinner("Радник читає знамення..."):
                final_answer, trace = run_agent(question, city, api_key)

            show_final_answer(final_answer)
            show_trace(trace)
        except groq.APIError as error:
            st.error(f"Помилка Groq API: {error}")
