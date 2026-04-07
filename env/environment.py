from pydantic import BaseModel
from typing import Dict, List

# ---------------- MODELS ---------------- #

class Observation(BaseModel):
    time_step: int
    warehouses: dict
    regions: dict
    cold_chain: dict
    supplier_status: str


class Action(BaseModel):
    ship_inventory: List[dict] = []
    rebalance: List[dict] = []
    prioritize_region: str = "critical"


# ---------------- ENV ---------------- #

class PharmaEnv:

    def __init__(self):
        self.reset("easy")

    def reset(self, task="easy"):
        self.task = task
        self.time_step = 0

        # Batch-level inventory
        self.inventory = {
            "W1": {
                "drugA": [{"qty": 50, "expiry": 3}, {"qty": 50, "expiry": 5}]
            },
            "W2": {
                "drugA": [{"qty": 80, "expiry": 4}]
            }
        }

        # Regions
        self.regions = {
            "R1": {"type": "critical", "demand": {"drugA": 40}},
            "R2": {"type": "normal", "demand": {"drugA": 60}}
        }

        # Cold chain
        self.cold_chain = {"W1": True, "W2": True}

        self.supplier_status = "active"

        # Transport routes
        self.routes = {
            ("W1", "R1"): {"cost": 5},
            ("W1", "R2"): {"cost": 2},
            ("W2", "R1"): {"cost": 3},
            ("W2", "R2"): {"cost": 4},
        }

        return self._get_obs()

    def step(self, action: Action):
        self.time_step += 1

        total_cost = 0
        waste = 0
        cold_penalty = 0
        fulfilled = 0
        critical_fulfilled = 0

        # -------- EXPIRY DECAY --------
        for w in self.inventory:
            for drug in self.inventory[w]:
                for batch in self.inventory[w][drug]:
                    batch["expiry"] -= 1

        # -------- REMOVE EXPIRED --------
        for w in self.inventory:
            for drug in self.inventory[w]:
                before = sum(b["qty"] for b in self.inventory[w][drug])
                self.inventory[w][drug] = [
                    b for b in self.inventory[w][drug] if b["expiry"] > 0
                ]
                after = sum(b["qty"] for b in self.inventory[w][drug])
                waste += max(0, before - after)

        # -------- EVENTS --------
        if self.task == "medium" and self.time_step == 2:
            self.supplier_status = "delayed"

        if self.task == "hard":
            if self.time_step == 1:
                self.supplier_status = "down"
            if self.time_step == 2:
                self.cold_chain["W1"] = False

        # -------- EMERGENCY SOURCING --------
        if self.supplier_status == "down":
            if "drugA" not in self.inventory["W2"]:
                self.inventory["W2"]["drugA"] = []
            self.inventory["W2"]["drugA"].append({"qty": 30, "expiry": 3})
            total_cost += 20  # penalty

        # -------- REBALANCING --------
        for move in action.rebalance:
            src = move["from"]
            dst = move["to"]
            qty = move["qty"]

            if "drugA" not in self.inventory.get(src, {}):
                continue

            batches = self.inventory[src]["drugA"]

            moved = 0
            for b in batches:
                if moved >= qty:
                    break
                take = min(b["qty"], qty - moved)
                b["qty"] -= take
                moved += take

            if dst not in self.inventory:
                self.inventory[dst] = {}

            if "drugA" not in self.inventory[dst]:
                self.inventory[dst]["drugA"] = []

            if moved > 0:
                self.inventory[dst]["drugA"].append({
                    "qty": moved,
                    "expiry": 3
                })

        # -------- COLD CHAIN FAILURE --------
        for w in self.cold_chain:
            if not self.cold_chain[w]:
                lost = sum(
                    b["qty"]
                    for drug in self.inventory[w]
                    for b in self.inventory[w][drug]
                )
                waste += lost
                self.inventory[w] = {}
                cold_penalty += 1

        # -------- APPLY SHIPMENTS --------
        for shipment in action.ship_inventory:
            w = shipment["from"]
            r = shipment["to"]
            qty = shipment["qty"]

            if (w, r) not in self.routes:
                continue

            route_cost = self.routes[(w, r)]["cost"]
            total_cost += route_cost * qty

            available = sum(
                b["qty"] for b in self.inventory.get(w, {}).get("drugA", [])
            )

            ship_qty = min(qty, available)

            # FIFO batch deduction
            remaining = ship_qty
            for batch in self.inventory.get(w, {}).get("drugA", []):
                if remaining <= 0:
                    break
                take = min(batch["qty"], remaining)
                batch["qty"] -= take
                remaining -= take

            # fulfill demand
            demand = self.regions[r]["demand"]["drugA"]
            f = min(ship_qty, demand)

            fulfilled += f
            self.regions[r]["demand"]["drugA"] -= f  # ✅ critical fix

            if self.regions[r]["type"] == "critical":
                critical_fulfilled += f

        # -------- METRICS --------
        total_demand = sum(r["demand"]["drugA"] for r in self.regions.values())
        total_demand = max(1, total_demand)

        fulfillment_ratio = fulfilled / total_demand
        critical_ratio = critical_fulfilled / total_demand

        cost_penalty = total_cost * 0.001
        waste_penalty = waste * 0.01

        # -------- REWARD --------
        reward = (
            0.35 * fulfillment_ratio +
            0.25 * critical_ratio -
            0.15 * cost_penalty -
            0.15 * waste_penalty -
            0.10 * cold_penalty
        )

        reward = max(0.0, min(1.0, reward))

        return {
            "observation": self._get_obs(),
            "reward": reward,
            "done": self.time_step >= 5
        }

    def state(self):
        return {
            "time_step": self.time_step,
            "warehouses": self.inventory,
            "regions": self.regions,
            "cold_chain": self.cold_chain,
            "supplier_status": self.supplier_status
        }

    def _get_obs(self):
        return Observation(
            time_step=self.time_step,
            warehouses=self.inventory,
            regions=self.regions,
            cold_chain=self.cold_chain,
            supplier_status=self.supplier_status
        )