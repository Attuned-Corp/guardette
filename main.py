import os

from dotenv import load_dotenv
from fastapi import FastAPI

from guardette import Guardette

load_dotenv()

policy_path = os.environ.get("GUARDETTE_POLICY_PATH")
if not policy_path:
    raise RuntimeError("GUARDETTE_POLICY_PATH environment variable must be set.")

guardette = Guardette(policy_path=policy_path)
app = FastAPI()


guardette.to_fastapi(app)
