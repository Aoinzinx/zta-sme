"""
AWS Lambda demonstration service — simulates a Nepali SME financial data API.
Fronted by API Gateway with a resource policy restricting invocations to the
Zero Trust Gateway's Elastic IP address only.
"""

import json
from datetime import datetime

SAMPLE_RECORDS = [
    {
        "id": "INV-2024-0841",
        "client": "Himalayan Traders Pvt Ltd",
        "amount_npr": 125000,
        "status": "paid",
        "date": "2024-11-15",
    },
    {
        "id": "INV-2024-0842",
        "client": "Kathmandu Digital Solutions",
        "amount_npr": 87500,
        "status": "pending",
        "date": "2024-11-28",
    },
    {
        "id": "INV-2024-0843",
        "client": "Nepal Tech Imports",
        "amount_npr": 234000,
        "status": "overdue",
        "date": "2024-10-30",
    },
]


def handler(event, context):
    """Lambda handler — returns simulated financial records for Nepali SMEs."""
    method = event.get("httpMethod", "GET")
    path   = event.get("path", "/")

    if method == "GET" and path == "/data":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "service":   "AWS Lambda demo",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "records":   SAMPLE_RECORDS,
            }),
        }

    if method == "GET" and path == "/health":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok"}),
        }

    return {
        "statusCode": 404,
        "body": json.dumps({"detail": "Not found"}),
    }
