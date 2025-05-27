import requests
from bs4 import BeautifulSoup

def fetch_resume_markdown(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Извлекаем заголовок резюме
    title = soup.find("h2")
    title_text = title.get_text(strip=True) if title else "Нет заголовка"

    # Извлекаем основную информацию о резюме
    info_table = soup.find("table", class_="msg_table")
    info_lines = []
    if info_table:
        for row in info_table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                value = cols[1].get_text(strip=True)
                info_lines.append(f"- **{key}**: {value}")

    # Извлекаем текст описания
    description = soup.find("div", id="msg_div_msg")
    description_text = description.get_text(strip=True) if description else "Нет описания"

    # Формируем markdown
    markdown = f"# {title_text}\n\n"
    if info_lines:
        markdown += "## Информация\n" + "\n".join(info_lines) + "\n\n"
    markdown += f"## Описание\n{description_text}\n"

    return markdown

if __name__ == "__main__":
    url = "https://www.ss.lv/msg/ru/work/i-search-for-work/programmer/bphnc.html"
    md = fetch_resume_markdown(url)
    print(md)
