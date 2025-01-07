FROM python:3 AS build

LABEL developer="Duff89"
LABEL maintainer="armrus.org"

# Installing required build packages
RUN set -ex && \
    apt-get update && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ="Europe/Moscow"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

ENV PATH="/usr/local/bin:$PATH"
ENV LANG="C.UTF-8"

COPY requirements.txt /parse_avito/requirements.txt
# COPY AvitoParser.py /parse_avito/AvitoParser.py
COPY custom_exception.py /parse_avito/custom_exception.py
COPY db_service.py /parse_avito/db_service.py
COPY lang.py /parse_avito/lang.py
COPY locator.py /parse_avito/locator.py
COPY parser_cls.py /parse_avito/parser_cls.py
COPY settings.ini /parse_avito/settings.ini
COPY user_agent_pc.txt /parse_avito/user_agent_pc.txt
COPY xlsx_service.py /parse_avito/xlsx_service.py
COPY entrypoint.sh /parse_avito/entrypoint.sh
RUN chmod +x /parse_avito/entrypoint.sh

# будем собирать из параметров для создания контейнера
ENV URL_AVITO="https://www.avito.ru/sankt-peterburg/tovary_dlya_kompyutera?cd=1&q=%%D0%%B2%%D0%%B8%%D0%%B4%%D0%%B5%%D0%%BE%%D0%%BA%%D0%%B0%%D1%%80%%D1%%82%%D0%%B0+rtx"
ENV CHAT_ID_TG=0
ENV TG_TOKEN=""
ENV NUM_ADS_AVITO=3
ENV FREQ_AVITO=60
ENV KEYS_AVITO=""
ENV KEYS_BLACKS_AVITO=""
ENV MAX_PRICE_AVITO=200000000
ENV MIN_PRICE_AVITO=0
ENV GEO_AVITO=""
ENV PROXY_AVITO=""
ENV PROXY_CHANGE_IP_AVITO=""
ENV NEED_MORE_INFO_AVITO=1
ENV DEBUG_MODE_AVITO=1
ENV FAST_SPEED_AVITO=1
ENV MAX_VIEW_AVITO=0
ENV KEYS_BLACK_AVITO=""


WORKDIR /parse_avito
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
#    libgtk-4-1 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i --force-depends google-chrome-stable_current_amd64.deb
RUN apt --fix-broken install
# ENTRYPOINT ["python", "./parser_cls.py"]
ENTRYPOINT ["sh", "entrypoint.sh"]
