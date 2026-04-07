import requests
import os

BASE = os.getenv("API_BASE_URL", "http://localhost:7860")


def smart_policy(state):
    action = {
        "ship_inventory": [],
        "rebalance": [],
        "prioritize_region": "critical"
    }

    warehouses = state["warehouses"]
    regions = state["regions"]
    cold_chain = state["cold_chain"]
    time_step = state["time_step"]

    # -------------------------------
    # 🔥 1. DYNAMIC WAREHOUSE STRATEGY
    # -------------------------------
    # early: use W1
    # later: prefer W2 (resilience)
    if time_step >= 1:
        preferred_order = ["W2", "W1"]
    else:
        preferred_order = ["W1", "W2"]

    # -------------------------------
    # 🔥 2. PROACTIVE REBALANCING
    # -------------------------------
    if "W1" in warehouses and "drugA" in warehouses["W1"]:
        total_w1 = sum(b["qty"] for b in warehouses["W1"]["drugA"])

        if total_w1 > 20:
            action["rebalance"].append({
                "from": "W1",
                "to": "W2",
                "qty": 20
            })

    # -------------------------------
    # 🔥 3. REGION PRIORITY
    # -------------------------------
    sorted_regions = sorted(
        regions.items(),
        key=lambda x: (
            0 if x[1]["type"] == "critical" else 1,
            -x[1]["demand"]["drugA"]
        )
    )

    # -------------------------------
    # 🔥 4. SMART SHIPPING
    # -------------------------------
    for region, rdata in sorted_regions:

        demand = rdata["demand"]["drugA"]
        if demand <= 0:
            continue

        for w in preferred_order:

            if w not in warehouses:
                continue

            if not cold_chain.get(w, True):
                continue

            drugs = warehouses[w]

            if "drugA" not in drugs:
                continue

            batches = drugs["drugA"]
            total = sum(b["qty"] for b in batches)

            if total <= 0:
                continue

            # FIFO (earliest expiry first)
            batches.sort(key=lambda b: b["expiry"])

            qty = min(20, demand, total)

            action["ship_inventory"].append({
                "from": w,
                "to": region,
                "qty": qty
            })

            break

    return action


def run_task(task):
    print("[START]")
    print(f"task={task}")

    requests.get(f"{BASE}/reset?task={task}")

    total_reward = 0

    for _ in range(5):
        state = requests.get(f"{BASE}/state").json()

        # DEBUG (optional)
        # print("STATE:", state)

        action = smart_policy(state)

        res = requests.post(f"{BASE}/step", json=action).json()

        reward = res["reward"]
        total_reward += reward

        print("\n[STEP]")
        print(f"action={action}")
        print(f"reward={reward}")

    score = min(1.0, total_reward / 5)

    print("\n[END]")
    print(f"score={score}")


if __name__ == "__main__":
    for t in ["easy", "medium", "hard"]:
        run_task(t)