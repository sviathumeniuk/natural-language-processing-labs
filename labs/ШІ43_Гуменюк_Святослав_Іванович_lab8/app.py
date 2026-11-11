import groq
import streamlit as st

MODEL = "openai/gpt-oss-120b"

HUMOR_STYLES = {
    "Сатира": "висміюй вади, лицемірство чи абсурдність описаної ситуації",
    "Гротеск": "химерно перебільшуй і поєднуй реальне з фантастичним аж до абсурду",
    "Іронія": "кажи одне, маючи на увазі протилежне, з прихованою насмішкою",
    "Сарказм": "використовуй їдку, відверто глузливу іронію",
    "Гіпербола": "доводь кожну деталь до комічно неймовірних масштабів",
    "Абсурд": "порушуй логіку та здоровий глузд, зберігаючи цілком серйозний тон",
    "Пародія": "описуй буденний зміст пафосним високим стилем урочистої промови чи оди",
}

SYSTEM_PROMPT = """Ти — редактор-гуморист. Перепиши речення користувача у заданій гумористичній формі.
Правила:
- Збережи основний зміст і мову оригіналу.
- Поверни лише переписаний текст: без вступів, пояснень, лапок, заголовків і коментарів.
- Обсяг — не більше трьох речень."""


def humorize(text: str, style: str, api_key: str) -> str:
    response = groq.Groq(api_key=api_key).chat.completions.create(
        model=MODEL,
        temperature=0.9,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Форма: {style} — {HUMOR_STYLES[style]}.\nРечення: {text}"},
        ],
    )

    return response.choices[0].message.content.strip()


st.set_page_config(page_title="Гумористичний переписувач", page_icon="🎭")
st.title("Гумористичний переписувач")
st.write("Введіть звичайне речення, оберіть гумористичну форму і отримайте його смішну версію.")

api_key = st.text_input("Groq API ключ", type="password", placeholder="gsk_...").strip()
text = st.text_area("Речення").strip()
style = st.selectbox("Гумористична форма", list(HUMOR_STYLES))

if st.button("Переписати", type="primary"):
    if not api_key:
        st.error("Вкажіть Groq API ключ.")
    elif not text:
        st.error("Введіть речення.")
    else:
        try:
            with st.spinner("Пишу..."):
                st.success(humorize(text, style, api_key))
        except groq.APIError as error:
            st.error(f"Помилка Groq API: {error}")
