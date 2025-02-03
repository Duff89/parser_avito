#!/bin/sh
sed -i "s|url = .*|url = $URL_AVITO|1" settings.ini
sed -i "s|chat_id=.*|chat_id= $CHAT_ID_TG|1" settings.ini
sed -i "s|tg_token = .*|tg_token = $TG_TOKEN|1" settings.ini
sed -i "s|num_ads = .*|num_ads = $NUM_ADS_AVITO|1" settings.ini
sed -i "s|freq = .*|freq = $FREQ_AVITO|1" settings.ini
sed -i "s|keys = .*|keys = $KEYS_AVITO|1" settings.ini
sed -i "s|keys_blacks = .*|keys_blacks = $KEYS_BLACKS_AVITO|1" settings.ini
sed -i "s|max_price = .*|max_price = $MAX_PRICE_AVITO|1" settings.ini
sed -i "s|min_price = .*|min_price = $MIN_PRICE_AVITO|1" settings.ini
sed -i "s|geo = .*|geo = $GEO_AVITO|1" settings.ini
sed -i "s|proxy = .*|proxy = $PROXY_AVITO|1" settings.ini
sed -i "s|proxy_change_ip = .*|proxy_change_ip = $PROXY_CHANGE_IP_AVITO|1" settings.ini
sed -i "s|need_more_info = .*|need_more_info = $NEED_MORE_INFO_AVITO|1" settings.ini
sed -i "s|debug_mode = .*|debug_mode = $DEBUG_MODE_AVITO|1" settings.ini
sed -i "s|fast_speed = .*|fast_speed = $FAST_SPEED_AVITO|1" settings.ini
sed -i "s|max_view = .*|max_view = $MAX_VIEW_AVITO|1" settings.ini
sed -i "s|keys_black = .*|keys_black = $KEYS_BLACK_AVITO|1" settings.ini
python parser_cls.py
