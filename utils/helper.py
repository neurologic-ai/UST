from loguru import logger
from odmantic import AIOEngine


async def get_popular_recommendation(engine: AIOEngine, top_n: int, model, filters: dict):
    print(f"[Popular] Filters: {filters}")

    # Fetch all matching documents (i.e., all chunks)
    docs = await engine.find(model, filters)
    if not docs:
        print("[Popular] No matching documents found")
        return {}, []

    combined_popular = {}

    # Merge counts across all chunks
    for doc in docs:
        if not doc.popular_data:
            continue
        for name, val in doc.popular_data.items():
            if name not in combined_popular:
                combined_popular[name] = val
            else:
                combined_popular[name].count += val.count

    if not combined_popular:
        print("[Popular] No popular_data across chunks")
        return {}, []

    sorted_items = sorted(
        combined_popular.items(),
        key=lambda item: item[1].count,
        reverse=True
    )

    top_names = [name for name, _ in sorted_items[:top_n]]
    return combined_popular, top_names


async def get_association_recommendations(engine: AIOEngine, cart_items: list, top_n: int, model, filters: dict):
    print(f"[Association] Base filters: {filters}")
    combined_assocs = {}

    for product in cart_items:
        filters_with_product = filters.copy()
        filters_with_product['product'] = product

        # Fetch all matching documents (across chunks)
        docs = await engine.find(model, filters_with_product)

        for doc in docs:
            if not doc.associate_products:
                continue

            for name, val in doc.associate_products.items():
                if name not in combined_assocs:
                    combined_assocs[name] = val
                else:
                    combined_assocs[name].count += val.count

    if not combined_assocs:
        print("[Association] No associated products found")
        return {}, []

    sorted_items = sorted(combined_assocs.items(), key=lambda x: x[1].count, reverse=True)
    top_names = [name for name, _ in sorted_items[:top_n]]
    return combined_assocs, top_names
