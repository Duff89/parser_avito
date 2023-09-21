from selenium.webdriver.common.by import By


class LocatorAvito:
    """Все необходимые селекторы"""
    NEXT_BTN = (By.CSS_SELECTOR, "[data-marker*='pagination-button/next']")
    TITLES = (By.CSS_SELECTOR, "[data-marker='item']")
    NAME = (By.CSS_SELECTOR, "[itemprop='name']")
    DESCRIPTIONS = (By.CSS_SELECTOR, "[class*='item-description']")
    URL = (By.CSS_SELECTOR, "[data-marker='item-title']")
    PRICE = (By.CSS_SELECTOR, "[itemprop='price']")
    TOTAL_VIEWS = (By.CSS_SELECTOR, "[data-marker='item-view/total-views']")
    DATE_PUBLIC = (By.CSS_SELECTOR, "[data-marker='item-view/item-date']")
    SELLER_NAME = (By.CSS_SELECTOR, "[data-marker='seller-info/label']")
    COMPANY_NAME = (By.CSS_SELECTOR, "[data-marker='seller-link/link']")
    COMPANY_NAME_TEXT = (By.CSS_SELECTOR, "span")
    GEO = (By.CSS_SELECTOR, "[class*='style-item-address']")

