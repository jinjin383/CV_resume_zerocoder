import requests
from bs4 import BeautifulSoup

def get_resume_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    response.raise_for_status()
    return response.text

def extract_resume_data(html):
    soup = BeautifulSoup(html, "html.parser")

    # Название резюме
    title_tag = soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Без названия"

    # Поиск всех пар "Ключ: Значение" из любых тегов (SS.lv любит менять верстку)
    resume_data = {}

    # Ищем все блоки, где, вероятно, есть ключ-значение (обычно td)
    for td in soup.find_all("td"):
        b = td.find("b")
        if b and b.next_sibling:
            key = b.get_text(strip=True).replace(":", "")
            value = b.next_sibling.strip(" :\n\r\t")
            if value:
                resume_data[key] = value

    # Описание (основной текст)
    desc_tag = soup.find("div", id="msg_div_msg")
    if desc_tag:
        description = desc_tag.get_text("\n", strip=True)
    else:
        description = ''

    # Если ничего не найдено, пытаемся хотя бы найти обычный текст в div-ах
    if not resume_data:
        possible_blocks = soup.find_all("div", class_="msg_body")
        for block in possible_blocks:
            text = block.get_text(" ", strip=True)
            if text:
                resume_data["Информация"] = text

    # Собираем всё в markdown
    md = f"# {title}\n\n"
    if not resume_data:
        md += "_Данные о резюме не найдены._\n\n"
    else:
        for k, v in resume_data.items():
            md += f"**{k}:** {v}\n\n"
    md += "## Описание\n\n"
    md += description if description else "_Описание не найдено_"

    return md.strip()

# --- Проверка кода (раскомментируйте для проверки на своем компьютере) ---
# html = get_resume_html("https://www.ss.lv/msg/lv/work/i-search-for-work/programmer/bphnc.html")
# print(extract_resume_data(html))
