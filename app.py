import streamlit as st
import pypdf
import google.generativeai as genai
import json

st.set_page_config(page_title="TenderAI — Анализатор", layout="wide")
st.title("📊 Постобработка и анализ госзакупок")

# Боковая панель для бесплатного ключа нейросети
st.sidebar.header("Настройки AI")
api_key = st.sidebar.text_input("Введите ваш Gemini API Key:", type="password")
st.sidebar.markdown("[Получить ключ бесплатно в Google AI Studio](https://aistudio.google.com/)")

uploaded_file = st.file_uploader("Загрузите итоговый протокол тендера (PDF)", type=["pdf"])

if uploaded_file:
    if not api_key:
        st.warning("👈 Пожалуйста, введите ваш Gemini API Key на панели слева.")
    else:
        genai.configure(api_key=api_key)
        
        with st.spinner("Читаем документ..."):
            # Извлекаем текст из PDF
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        
        if st.button("🚀 Запустить AI-анализ"):
            with st.spinner("Нейросеть анализирует текст и извлекает данные..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Четкая инструкция для ИИ, чтобы он вернул структурированный JSON
                prompt = f"""
                Ты эксперт по государственным закупкам. Проанализируй текст протокола итогов и извлеки данные строго в формате JSON.
                Если какого-то поля нет, напиши null. Не придумывай данные, которых нет в тексте.
                Ответь ТОЛЬКО чистым JSON, без лишних слов.
                
                Структура JSON:
                {{
                  "lot_number": "номер лота или контракта",
                  "subject": "предмет закупки (что закупают)",
                  "winner_name": "название компании-победителя",
                  "winner_bin": "БИН победителя",
                  "initial_price": "стартовая (выделенная) сумма числом",
                  "final_price": "финальная цена победителя числом",
                  "rejected_companies": [
                     {{"name": "название отклоненного участника", "reason": "краткая понятная причина отклонения на русском языке"}}
                  ]
                }}

                Текст для анализа:
                {text[:30000]}
                """
                
                try:
                    response = model.generate_content(prompt)
                    res_text = response.text.strip()
                    
                    # Очищаем ответ от возможных markdown-тегов ```json
                    if "```json" in res_text:
                        res_text = res_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in res_text:
                        res_text = res_text.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(res_text)
                    
                    st.success("Анализ успешно завершен!")
                    
                    # Вывод главных метрик
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Номер лота", data.get("lot_number", "—"))
                    col2.metric("Выделенная сумма", f"{data.get('initial_price', 0)} ₸")
                    col3.metric("Цена победителя", f"{data.get('final_price', 0)} ₸")
                    
                    st.subheader("🏆 Победитель тендера")
                    st.info(f"**{data.get('winner_name', 'Не указан')}** (БИН: {data.get('winner_bin', '—')})")
                    
                    st.subheader("❌ Отклоненные участники и причины (Анализ ошибок)")
                    if data.get("rejected_companies"):
                        st.table(data["rejected_companies"])
                    else:
                        st.write("Отклоненных участников не обнаружено.")
                        
                except Exception as e:
                    st.error(f"Ошибка распознавания. Попробуйте еще раз. Техническая ошибка: {e}")
