from typing import List

from loguru import logger

from dto import AvitoConfig
from models import Item


class AdsFilter:
    def __init__(self, config: AvitoConfig, is_viewed_fn=None):
        self.config = config
        self.is_viewed_fn = is_viewed_fn

    def apply(self, ads: List[Item]) -> List[Item]:
        """Применяет все фильтры по порядку"""
        filters = [
            self._filter_viewed,
            self._filter_by_price_range,
            self._filter_by_black_keywords,
            self._filter_by_white_keyword,
            self._filter_by_address,
            self._filter_by_seller,
            self._filter_by_recent_time,
            self._filter_by_reserve,
            self._filter_by_promotion,
        ]

        for filter_fn in filters:
            ads = filter_fn(ads)
            logger.info(f"После фильтрации {filter_fn.__name__} осталось {len(ads)}")
            if not ads:
                return ads
        return ads

    def _filter_viewed(self, ads: List[Item]) -> List[Item]:
        if self.is_viewed_fn:
            return [ad for ad in ads if not self.is_viewed_fn(ad)]
        return ads

    def _filter_by_price_range(self, ads: List[Item]) -> List[Item]:
        min_p = self.config.min_price or 0
        max_p = self.config.max_price if (self.config.max_price is not None and self.config.max_price > 0) else float("inf")
        if min_p == 0 and max_p == float("inf"):
            return ads
        filtered = []
        for ad in ads:
            val = (
                ad.priceDetailed.value
                if (ad.priceDetailed and getattr(ad.priceDetailed, "value", None) is not None)
                else 0
            )
            if min_p <= val <= max_p:
                filtered.append(ad)
        return filtered

    def _filter_by_black_keywords(self, ads: List[Item]) -> List[Item]:
        if not self.config.keys_word_black_list:
            return ads
        return [ad for ad in ads if not self._is_phrase_in_ads(ad, self.config.keys_word_black_list)]

    def _filter_by_white_keyword(self, ads: List[Item]) -> List[Item]:
        if not self.config.keys_word_white_list:
            return ads
        return [ad for ad in ads if self._is_phrase_in_ads(ad, self.config.keys_word_white_list)]

    def _filter_by_address(self, ads: List[Item]) -> List[Item]:
        if not self.config.geo or not self.config.geo.strip():
            return ads
        geo_target = self.config.geo.strip().lower()
        return [
            ad for ad in ads
            if ad.geo and getattr(ad.geo, "formattedAddress", None) and geo_target in ad.geo.formattedAddress.lower()
        ]

    def _filter_by_seller(self, ads: List[Item]) -> List[Item]:
        if not self.config.seller_black_list:
            return ads
        return [ad for ad in ads if not getattr(ad, "sellerId", None) or ad.sellerId not in self.config.seller_black_list]

    def _filter_by_recent_time(self, ads: List[Item]) -> List[Item]:
        if not self.config.max_age:
            return ads
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        filtered = []
        for ad in ads:
            if not ad.sortTimeStamp:
                continue
            try:
                published = datetime.fromtimestamp(ad.sortTimeStamp / 1000, tz=timezone.utc)
                if (now - published) <= timedelta(seconds=self.config.max_age):
                    filtered.append(ad)
            except Exception:
                continue
        return filtered

    def _filter_by_reserve(self, ads: List[Item]) -> List[Item]:
        if not self.config.ignore_reserv:
            return ads
        return [ad for ad in ads if not getattr(ad, "isReserved", False)]

    def _filter_by_promotion(self, ads: List[Item]) -> List[Item]:
        if not self.config.ignore_promotion:
            return ads
        for ad in ads:
            steps = (ad.iva or {}).get("DateInfoStep") if isinstance(ad.iva, dict) else []
            ad.isPromotion = any(
                isinstance(v, dict) and v.get("title") == "Продвинуто"
                for step in (steps or [])
                for v in (
                    (getattr(step, "payload", None) or (step.get("payload") if isinstance(step, dict) else None) or {}).get("vas")
                    or []
                )
            )
        return [ad for ad in ads if not ad.isPromotion]

    @staticmethod
    def _is_phrase_in_ads(ad: Item, phrases: list) -> bool:
        full_text = ((ad.title or "") + (ad.description or "")).lower()
        return any(phrase.lower() in full_text for phrase in phrases)
