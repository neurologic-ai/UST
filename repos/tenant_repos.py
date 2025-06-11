from models.db import Tenant


def validate_location_store_access(
    tenant: Tenant,
    location_id: str,
    store_id: str
) -> bool:
    # Find the location
    matching_location = next(
        (loc for loc in tenant.locations if loc.location_id == location_id), None
    )

    if not matching_location:
        return False

    # Check if store exists in that location
    matching_store = next(
        (store for store in matching_location.stores if store.store_id == store_id), None
    )

    return matching_store is not None
