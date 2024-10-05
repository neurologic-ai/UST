def insert_data(collection_name, inp_data, many = True, dataset_name = ''):
    collection_name.delete_many({})
    if many:
        collection_name.insert_many(inp_data)
    else:
        collection_name.insert_one(inp_data)
    print(f"{dataset_name} data stored successfully!")