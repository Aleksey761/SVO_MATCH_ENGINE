from .models import ArrivalItem, MasterItem


class Matcher:
    """Matches normalized arrival items against MASTER."""

    def __init__(self, master_items: list[MasterItem]):
        self.index: dict[str, MasterItem] = {
            item.normalized_key: item for item in master_items
        }

    def match(self, item: ArrivalItem) -> ArrivalItem:
        master = self.index.get(item.normalized_key)

        if master is None:
            item.status = "REVIEW"
            return item

        item.sku = master.sku
        item.master_name = (
            f"{master.category} {master.brand} "
            f"{master.variant} {master.volume}"
        )
        item.status = "MATCH"
        return item

    def match_all(self, items: list[ArrivalItem]) -> list[ArrivalItem]:
        return [self.match(item) for item in items]
