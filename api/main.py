from fastapi import FastAPI
from env.environment import PharmaEnv, Action

app = FastAPI()
env = PharmaEnv()

@app.get("/reset")
def reset(task: str = "easy"):
    return env.reset(task)

@app.post("/step")
def step(action: Action):
    return env.step(action)

@app.get("/state")
def state():
    return env.state()