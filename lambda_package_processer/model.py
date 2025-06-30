import pandas as pd
from collections import defaultdict
from constant import QUANTITY_COL, PRODUCT_NAME_COL, SESSION_COL, UPC_COL



def popular_based(df, tenant_id, top_n=100):
    results = []

    for (location_id, store_id), group in df.groupby(['location_id', 'store_id']):
        # Sum quantities for each product+UPC combo
        grouped = group.groupby([PRODUCT_NAME_COL, UPC_COL])[QUANTITY_COL].sum().reset_index()

        # Get top N by quantity
        top_products = grouped.sort_values(by=QUANTITY_COL, ascending=False).head(top_n)

        # Convert to expected dict format: name -> {upc, count}
        popular_data = {
            row[PRODUCT_NAME_COL]: {
                "upc": row[UPC_COL],
                "count": int(row[QUANTITY_COL])
            }
            for _, row in top_products.iterrows()
            if str(row[PRODUCT_NAME_COL]).strip()
        }

        results.append({
            "tenant_id": tenant_id,
            "location_id": location_id,
            "store_id": store_id,
            "popular_data": popular_data
        })

    return results


def association_based(df: pd.DataFrame,tenant_id, top_n=100) -> list:
    full_result = []

    for (location_id, store_id), store_group in df.groupby(["location_id", "store_id"]):
        association_cache = defaultdict(lambda: defaultdict(int))
        upc_lookup = defaultdict(str)

        # Group by sessions within each store
        for _, session_data in store_group.groupby(SESSION_COL):
            products = session_data[[PRODUCT_NAME_COL, UPC_COL, QUANTITY_COL]]

            names = products[PRODUCT_NAME_COL].tolist()
            upcs = products[UPC_COL].tolist()
            quantities = products[QUANTITY_COL].tolist()

            for i, (name_i, upc_i, qty_i) in enumerate(zip(names, upcs, quantities)):
                upc_lookup[name_i] = upc_i  # Ensure UPC is recorded
                for j, (name_j, upc_j, qty_j) in enumerate(zip(names, upcs, quantities)):
                    if i != j:
                        association_cache[name_i][name_j] += qty_j
                        upc_lookup[name_j] = upc_j

        # Prepare result with sorted top N associated products
        for product, associates in association_cache.items():
            sorted_associates = sorted(associates.items(), key=lambda x: x[1], reverse=True)[:top_n]

            associate_products = {
                associate_name: {
                    "upc": upc_lookup[associate_name],
                    "count": int(count)
                }
                for associate_name, count in sorted_associates
                if associate_name.strip()
            }

            full_result.append({
                "tenant_id": tenant_id,
                "location_id": location_id,
                "store_id": store_id,
                "product": product,  # key is product name, not UPC
                "associate_products": associate_products
            })

    return full_result
