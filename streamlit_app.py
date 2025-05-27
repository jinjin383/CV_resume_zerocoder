import streamlit as st
from openai import OpenAI
from parse_cv_lv_m_i import get_html, extract_vacancy_data
from parse_ss_lv_gpt import get_resume_html, extract_resume_data

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_PROMPT = """
Проверь резюме кандидата, насколько он хорошо подходит к данной вакансии.
Сначала напиши короткий анализ, который будет пояснять оценку.
Поставь оценку  качеству резюме от 1 до 10. Из резюме должно быть понятно, 
с какими задачами и проблемами сталкивался кандидат и как именно он их решал. Описаны ли результаты и достижения?
Нам важно нанимать людей, которые серьезно относятся к заполнению резюме, к анализу своей работы и влиянию на компанию.
Потом поставь оцеку соответствия кандидата вакансии от 1 до 10. На эту оценку должна влиять оценка качества резюме.
Поставь итоговою оценку от 0 до 10.
""".strip()

def request_gpt(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},  
            {"role": "user", "content": user_prompt},     
        ],
        max_tokens=1000,
        temperature=0,
    )
    return response.choices[0].message.content

st.title('CV Scoring App')

job_description = st.text_area('Введите ссылку на вакансию')
cv = st.text_area('Введите ссылку на резюме')

if st.button("Проанализировать соответствие"):
    with st.spinner("Парсим данные и отправляем в GPT..."):
        try:
            job_html = get_html(job_description)
            resume_html = get_resume_html(cv)
            job_text = extract_vacancy_data(job_html)
            resume_text = extract_resume_data(resume_html)
            prompt = f"# ВАКАНСИЯ\n{job_text}\n\n# РЕЗЮМЕ\n{resume_text}"
            response = request_gpt(SYSTEM_PROMPT, prompt)
            st.subheader("📊 Результат анализа:")
            st.markdown(response)
        except Exception as e:
            st.error(f"Произошла ошибка: {e}")