from odmantic.query import and_  # ODMantic's logical AND
from functools import reduce

def build_nested_and(conditions):
    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return reduce(lambda a, b: and_(a, b), conditions)
