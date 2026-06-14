import httpx

r = httpx.get("http://127.0.0.1:8000/api/campaigns")
campaigns = r.json()["campaigns"]

for c in campaigns[:5]:
    r2 = httpx.get(f"http://127.0.0.1:8000/api/campaigns/{c['id']}")
    stats = r2.json()["stats"]
    print(f"Campaign: {c['intent'][:45]}")
    print(f"  Total:{stats['total']} Delivered:{stats['delivered']} Opened:{stats['opened']} Clicked:{stats['clicked']} Converted:{stats['converted']} Revenue:{stats['revenue']}")
    print()