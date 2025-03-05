import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from main import fetch_tender_links


def test_fetch_tender_links_parse_and_extract(self):
    mock_browser = MagicMock()
    mock_browser.page_source = '''
    <div class="registry-entry__header-mid__number">
        <a href="/link1?regNumber=123456&otherParam=value">Link 1</a>
    </div>
    <div class="registry-entry__header-mid__number">
        <a href="/link2?regNumber=789012&otherParam=value">Link 2</a>
    </div>
    '''

    with patch('main.webdriver.Chrome', return_value=mock_browser), \
            patch('main.time.sleep'):
        result = fetch_tender_links(1)

    expected_links = [
        'https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber=123456',
        'https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber=789012'
    ]
    self.assertEqual(result, expected_links)

