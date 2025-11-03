import urllib.parse

def generate_urls_from_query(queries):
    """
    Генерирует URL-адреса Avito из списка поисковых запросов.
    Поддерживает запросы с указанием города и категории.
    Пример: "бульдозер москва спецтехника"
    """
    urls = []
    for query in queries:
        parts = query.lower().split()
        search_terms = []
        city = "all"
        category = ""

        # Примерная логика для определения города и категории
        # Это можно значительно усложнить для большей точности
        if len(parts) > 1:
            # Проверяем, является ли последнее слово известным городом
            # (в реальном приложении здесь был бы словарь городов)
            if parts[-1] in ["moskva", "krasnodar", "sankt-peterburg"]:
                city = parts.pop()
        
        if len(parts) > 1:
             # Проверяем, является ли последнее слово известной категорией
            if parts[-1] in ["gruzoviki_i_spetstehnika", "telefony"]:
                category = parts.pop()

        search_terms = parts
        search_query = " ".join(search_terms)
        encoded_query = urllib.parse.quote(search_query)

        # Формируем URL
        if category:
            url = f"https://www.avito.ru/{city}/{category}?q={encoded_query}"
        else:
            url = f"https://www.avito.ru/{city}?q={encoded_query}"
        urls.append(url)
        
    return urls