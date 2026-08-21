

class MockedRetriever:
    def __init__(self):
        self.data = [
            {"name": "经济套餐", "price": 20, "data": 10},
            {"name": "畅游套餐", "price": 50, "data": 100},
            {"name": "超级套餐", "price": 200, "data": 1000}
        ]

    def retrieve(self, **kwargs):
        records = []
        try:
            for r in self.data:
                select = True
                for k, v in kwargs.items():
                    if k == "sort":
                        continue
                    if k == "data" and v["value"] == "无上限":
                        if r[k] != 1000:
                            select = False
                            break
                    if "operator" in v:
                        if not isinstance(v["value"], int):
                            if v["operator"].find(">") >= 0:
                                v["value"] = 0
                            else:
                                v["value"] = 1000

                        if not eval(str(r[k])+v["operator"]+str(v["value"])):
                            select = False
                            break
                    elif str(r[k]) != str(v):
                        select = False
                        break
                if select:
                    records.append(r)
        except:
            return []
        
        if len(records) <= 1:
            return records

        key = "price"
        reverse = False

        if "sort" in kwargs:
            key = kwargs["sort"]["value"]
            reverse = kwargs["sort"]["ordering"] == "descend"

        return sorted(records, key=lambda x: x[key], reverse=reverse)    
