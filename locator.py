from selenium.webdriver.common.by import By

class LocatorAvito:
    NEXT_BTN = (By.CSS_SELECTOR, "[data-marker*='pagination-button/next']")
    TITLES = (By.CSS_SELECTOR, "[data-marker='item']")
    NAME = (By.CSS_SELECTOR, "[itemprop='name']")
    DESCRIPTIONS = (By.CSS_SELECTOR, "[class*='item-description']")
    URL = (By.CSS_SELECTOR, "[data-marker='item-title']")
    PRICE = (By.CSS_SELECTOR, "[itemprop='price']")