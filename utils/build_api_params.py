from utils.normalize_parametr import normalize_params


def build_api_params(search_core: dict) -> dict:
    params = {}

    base_keys = [
        'categoryId',
        'locationId',
        'verticalCategoryId',
        'rootCategoryId',
        'localPriority',
        'geoCoords',
    ]

    for key in base_keys:
        value = search_core.get(key)
        if value not in (None, [], ''):
            params[key] = str(value)

    # цена
    if search_core.get('priceMax'):
        params['pmax'] = search_core['priceMax']

    if search_core.get('priceMin'):
        params['pmin'] = search_core['priceMin']

    # продавец
    if search_core.get('owner'):
        params['user'] = search_core['owner']

    # доставка
    if search_core.get('withDeliveryOnly'):
        params['cd'] = 1

    # радиус
    if search_core.get('searchRadius'):
        params['radius'] = search_core['searchRadius']

    # сложные фильтры
    if search_core.get('params'):
        params.update(normalize_params(search_core['params']))

    return params