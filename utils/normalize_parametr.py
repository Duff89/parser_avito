def normalize_params(params_dict: dict) -> dict:
    result = {}

    for key, values in params_dict.items():
        if not values:
            continue

        # если список
        if isinstance(values, list):
            for i, v in enumerate(values):
                # чаще всего работает без индекса
                result[f'params[{key}]'] = str(v)

        else:
            result[f'params[{key}]'] = str(values)

    return result