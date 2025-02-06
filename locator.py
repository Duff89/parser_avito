from selenium.webdriver.common.by import By


class LocatorAvito:
    """Все необходимые селекторы"""
    TITLES = (By.CSS_SELECTOR, "div[itemtype*='http://schema.org/Product']")
    NAME = (By.CSS_SELECTOR, "[itemprop='name']")
    DESCRIPTIONS = (By.CSS_SELECTOR, "meta[itemprop='description']")
    DESCRIPTIONS_FULL_PAGE = (By.CSS_SELECTOR, "[data-marker='item-view/item-description']")
    URL = (By.CSS_SELECTOR, "[itemprop='url']")
    PRICE = (By.CSS_SELECTOR, "[itemprop='price']")
    TOTAL_VIEWS = (By.CSS_SELECTOR, "[data-marker='item-view/total-views']")
    DATE_PUBLIC = (By.CSS_SELECTOR, "[data-marker='item-view/item-date']")
    SELLER_NAME = (By.CSS_SELECTOR, "[data-marker='seller-info/label']")
    SELLER_LINK = (By.CSS_SELECTOR, "[data-marker='seller-link/link']")
    COMPANY_NAME = (By.CSS_SELECTOR, "[data-marker='seller-link/link']")
    COMPANY_NAME_TEXT = (By.CSS_SELECTOR, "span")
    GEO = (By.CSS_SELECTOR, "div[class*='style-item-address']")

