import requests
from bs4 import BeautifulSoup
from celery import Celery, group
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from config import CeleryConfig

# Создаем экземпляр Celery
app = Celery('main')

# Применяем конфигурацию
app.config_from_object(CeleryConfig)



@app.task(name='main.fetch_tender_links')
def fetch_tender_links(page_number: int) -> list[str]:
    '''
    Получает список ссылок на тендеры с указанной страницы.

    Args: page_number (int): Номер страницы для парсинга
    Returns: list[str]: Список ссылок на печатные формы тендеров
    '''

    try:
        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Chrome(options=options)

        url = f'https://zakupki.gov.ru/epz/order/extendedsearch/results.html?morphology=on&pageNumber={page_number}&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=UPDATE_DATE&fz44=on&pc=on'
        browser.get(url)
        time.sleep(2)

        soup = BeautifulSoup(browser.page_source, 'html.parser')
        tender_blocks = soup.find_all('div', class_='registry-entry__header-mid__number')

        links = []
        for block in tender_blocks:
            link = block.find('a')
            if link and 'href' in link.attrs:
                href = link['href']
                reg_number = href.split('regNumber=')[1].split('&')[0]
                print_form_url = f'https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={reg_number}'
                links.append(print_form_url)

        return links

    except WebDriverException as e:
        print(f"Ошибка браузера: {str(e)}")
        return []

    except Exception as e:
        print(f"Неожиданная ошибка: {str(e)}")
        return []



def get_headers():
    return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/xml'
    }


@app.task(name='main.parse_tender_xml')
def parse_tender_xml(url: str) -> tuple[str, str]:
    '''
    Извлекает дату публикации из XML тендера.

    Args:url (str): URL печатной формы тендера
    Returns:tuple[str, str]: Кортеж (url, дата публикации)
    '''

    try:
        # Получаем regNumber из URL
        reg_number = url.split('regNumber=')[1]

        # Формируем правильный URL для XML
        xml_url = f'https://zakupki.gov.ru/epz/order/notice/printForm/viewXml.html?regNumber={reg_number}'

        session = requests.Session()
        response = session.get(xml_url, headers=get_headers())

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'xml')
            publish_date = soup.find('publishDTInEIS')

            if publish_date:
                return url, publish_date.text

        raise Exception("Дата публикации не найдена")

    except requests.RequestException as e:
        print(f"Ошибка запроса {url}: {str(e)}")
        return url, "Ошибка запроса"

    except Exception as e:
        print(f"Error {url}: {str(e)}")
        return url, "Дата не найдена"


if __name__ == "__main__":
    try:
        # Создаем группу задач для сбора ссылок
        link_tasks = group(fetch_tender_links.s(page) for page in range(1, 3))

        # Получаем все ссылки
        links_results = link_tasks.apply_async()
        all_links = []
        for page_links in links_results.get():
            all_links.extend(page_links)

        # Создаем группу задач для парсинга
        parse_tasks = group(parse_tender_xml.s(link) for link in all_links)
        results = parse_tasks.apply_async()

        # Печатаем результаты
        for result in results.get():
            print(f"Ссылка на печатную форму: {result[0]}")
            print(f"Дата публикации: {result[1].split('T')[0]}")
            print("-" * 80)

    except Exception as e:
        print(f"Критическая ошибка в основном блоке: {str(e)}")
