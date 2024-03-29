import aiohttp


async def fetch(
    url,
    payload=None,
    type_req="post",
    type_data="json",
    headers=None,
):
    if payload is None:
        payload = {}

    async with aiohttp.ClientSession() as session:
        if type_req == "post":
            req = session.post
        elif type_req == "put":
            req = session.put
        elif type_req == "delete":
            req = session.delete
        elif type_req == "patch":
            req = session.patch
        elif type_req == "options":
            req = session.options
        else:
            req = session.get

        async with req(
            url,
            headers=headers,
            **{type_data: payload},
        ) as response:
            code = response.status

            try:
                data = await response.json()
            except:  # noqa: E722
                data = await response.text()

            return code, data
