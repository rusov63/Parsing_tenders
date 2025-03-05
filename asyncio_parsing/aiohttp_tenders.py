import aiohttp
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import time
from typing import List, Tuple


async def fetch_tender_links(page_number: int) -> List[str]:
    '''
    Асинхронно получает список ссылок на тендеры с указанной страницы.
    '''
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            url = f'https://zakupki.gov.ru/epz/order/extendedsearch/results.html?morphology=on&pageNumber={page_number}&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=UPDATE_DATE&fz44=on&pc=on'
            await page.goto(url)
            await asyncio.sleep(2)

            content = await page.content()
            await browser.close()

            soup = BeautifulSoup(content, 'html.parser')
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

    except Exception as e:
        print(f"Ошибка при получении ссылок на странице {page_number}: {str(e)}")
        return []


async def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/xml'
    }


async def parse_tender_xml(session: aiohttp.ClientSession, url: str) -> Tuple[str, str]:
    '''
    Асинхронно извлекает дату публикации из XML тендера.
    '''
    try:
        reg_number = url.split('regNumber=')[1]
        xml_url = f'https://zakupki.gov.ru/epz/order/notice/printForm/viewXml.html?regNumber={reg_number}'

        async with session.get(xml_url, headers=await get_headers()) as response:
            if response.status == 200:
                text = await response.text()
                soup = BeautifulSoup(text, 'xml')
                publish_date = soup.find('publishDTInEIS')

                if publish_date:
                    return url, publish_date.text

            return url, "Дата не найдена"

    except Exception as e:
        print(f"Ошибка при парсинге {url}: {str(e)}")
        return url, "Ошибка парсинга"


async def main():
    try:
        # Получаем ссылки со всех страниц
        pages_range = range(1, 3)
        link_tasks = [fetch_tender_links(page) for page in pages_range]
        all_pages_links = await asyncio.gather(*link_tasks)

        # Объединяем все ссылки в один список
        all_links = [link for page_links in all_pages_links for link in page_links]

        # Создаем сессию для выполнения запросов
        async with aiohttp.ClientSession() as session:
            # Создаем задачи для парсинга
            parse_tasks = [parse_tender_xml(session, link) for link in all_links]
            results = await asyncio.gather(*parse_tasks)

            # Выводим результаты
            for result in results:
                print(f"Ссылка на печатную форму: {result[0]}")
                print(f"Дата публикации: {result[1].split('T')[0]}")
                print("-" * 80)

    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")



asyncio.run(main())
