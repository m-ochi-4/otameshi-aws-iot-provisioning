
import json


def lambda_handler(event, _):
    print(json.dumps(event, separators=(",", ":")))
    return {"allowProvisioning": True}
