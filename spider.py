from typing import Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common import StaleElementReferenceException, TimeoutException, ElementNotInteractableException, \
    NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd


class LunSpider:
    CHROME_DRIVER_PATH = r'C:\Users\user\Documents\GitHub\lun_selenium\drivers\chromedriver.exe'
    URL = 'https://lun.ua/'

    def __init__(self) -> None:
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.data = []

    def _create_driver(self) -> webdriver.Chrome:
        service = Service(self.CHROME_DRIVER_PATH)
        options = Options()
        # options.add_argument('--headless')
        return webdriver.Chrome(service=service, options=options)

    def run(self, city: str, category: str) -> None:
        """Controlling the main workflow"""
        self.start_request()
        self.select_city(city=city)
        self.select_building_category(category=category)
        self.select_radius()
        links = self.collect_links()
        for link in links:
            self.data.append(
                self.parse(link)
            )
        self.save()
        self.driver.quit()

    def start_request(self) -> None:
        self.driver.maximize_window()
        self.driver.get(url=self.URL)

    def select_city(self, city: str) -> None:
        """Opens a city panel and then selecting the city by link text
        City options: 'Київ', 'Рівне', 'Львів', 'Одеса' etc."""
        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//button[@data-event-label="update_city"]')
            )
        ).click()

        self.wait.until(
            EC.presence_of_element_located(
                (By.LINK_TEXT, city)
            )
        ).click()

    def select_building_category(self, category: str) -> None:
        """Category: Новобудови, Котеджі"""
        xpath = f'//div[@class="h2" and contains(text(), "{category.capitalize()}")]/..//a'
        self.driver.find_element(By.XPATH, xpath).click()

    def select_radius(self, radius: int = 0) -> None:
        """Changing the radius from the selected city for search.
        Currently working only for making it zero"""
        # Open the panel
        button = self.driver.find_element(By.CLASS_NAME, 'GeoControlDistance-trigger')
        button.click()

        # Locate slider, knob and find the width of element
        slider = self.driver.find_element(By.CSS_SELECTOR, 'div.GeoControlDistance-slider  div.noUi-connects')
        slider_width = slider.size.get('width')
        knob = self.driver.find_element(By.CSS_SELECTOR, 'div.GeoControlDistance-slider div.noUi-handle')

        # can get max value from knob
        max_value = float(knob.get_attribute('aria-valuemax'))

        # perform actions
        move = ActionChains(self.driver)
        move.click_and_hold(knob).move_by_offset(-slider_width, 0).release(knob).perform()

        # close the panel and wait
        button.click()
        self.wait.until(EC.invisibility_of_element(slider))

    def collect_links(self) -> list:
        """Going throw all pages dealing with pagination and collecting links for every object"""
        links = []
        while True:
            self.wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'Card-link')))
            for card in self.driver.find_elements(By.CLASS_NAME, 'Card-link'):
                link = card.get_attribute('href')
                links.append(link)
            next_page = self.driver.find_element(By.XPATH, '//div[@class="UIPagination"]/div[last()]')
            if '-disabled' in next_page.get_attribute('class'):
                break
            next_page.click()
        return links

    def retrieve(self, by: By, selector: str, attribute: Optional[str] = None) -> Any:
        """Wrapper for dealing with existing of an element"""
        try:
            if not attribute:
                value = self.driver.find_element(by, selector).text
            else:
                value = self.driver.find_element(by, selector).get_attribute(attribute)
        except NoSuchElementException:
            print('Element not found', by, selector, sep=' | ')
            value = None
        return value

    def parse(self, link: str) -> dict:
        data = {}

        self.driver.get(link)

        data['title'] = self.retrieve(By.CSS_SELECTOR, 'h1.h1')
        print(data['title'])

        data['city'] = self.retrieve(By.CLASS_NAME, 'BuildingContacts-breadcrumbs')

        data['location'] = self.retrieve(By.CSS_SELECTOR, '#location div.UISubtitle-content')

        data['sales'] = self.retrieve(By.CLASS_NAME, 'BuildingSaleStatus-developerOffer')

        data['construction'] = self.retrieve(By.CLASS_NAME, 'BuildingSaleStatus-queue')

        data['website'] = self.retrieve(
            By.XPATH, '//div[@id="building-contacts-content"]//a[1]//div[@class="UITwoLinerButton-content"]'
        )

        data['contact_phone'] = self.retrieve(By.XPATH, '//div[@id="building-contacts-content"]//a[2]', 'href')

        # TODO make a function for building attrs 'cause all selectors are the same
        data['building_class'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Клас")]/following-sibling::div'
        )

        data['number_of_buildings'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Будинків")]/following-sibling::div'
        )

        data['number_of_sections'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Секцій")]/following-sibling::div'
        )

        data['number_of_floors'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Поверховість")]/following-sibling::div'
        )

        data['construction_technology'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Технологія будівництва")]/following-sibling::div'
        )

        data['walls'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Стіни")]/following-sibling::div'
        )

        data['insulation'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Утеплення")]/following-sibling::div'
        )

        data['heating'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Опалення")]/following-sibling::div'
        )

        data['ceiling_height'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Висота стелі")]/following-sibling::div'
        )

        data['number_of_apartments'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Кількість квартир")]/following-sibling::div'
        )

        data['apartment_condition'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Стан квартири")]/following-sibling::div'
        )

        data['closed_territory'] = self.retrieve(
            By.XPATH,
            '//div[@class="BuildingAttributes-name" and contains(text(), "Закрита територія")]/following-sibling::div'
        )

        data['parking'] = self.retrieve(
            By.XPATH, '//div[@class="BuildingAttributes-name" and contains(text(), "Паркінг")]/following-sibling::div'
        )

        data['price'] = self.retrieve(By.CLASS_NAME, 'BuildingPrices-price')

        # TODO make it a nested DataFrame
        price_details = {}
        try:
            rows = self.driver.find_elements(By.XPATH, '//div[@class="BuildingPrices-content"]')
        except NoSuchElementException:
            print('No pricing details founded')
        else:
            for row in rows:
                name = self.get_pricing_details(row, By.XPATH, './/div[contains(@class, "BuildingPrices-main")]')
                square = self.get_pricing_details(
                    row, By.XPATH, './/div[contains(@class, "BuildingPrices-main")]/following-sibling::div'
                )
                from_price = self.get_pricing_details(
                    row, By.XPATH, './/div[contains(@class, "BuildingPrices-main")]/../descendant::span'
                )
                price_per_square_meter = self.get_pricing_details(row, By.XPATH, './/div[@data-currency="uah"]')

                price_details[name] = {'square': square, 'from_price': from_price, 'per_sq_m': price_per_square_meter}
        data['price_details'] = price_details

        print(data)
        return data

    @staticmethod
    def get_pricing_details(row, by, selector):
        try:
            value = row.find_element(by, selector).text
        except NoSuchElementException:
            print('Cant find', by, selector, sep=' | ')
            value = None
        return value

    def save(self) -> None:
        """Saving to csv"""
        df = pd.DataFrame(self.data)
        df.to_csv('data.csv', encoding='utf-8', index=False)


if __name__ == '__main__':
    spider = LunSpider()
    spider.run(city='Рівне', category='Новобудови')
