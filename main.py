from fastapi import FastAPI

from guardette import Guardette
from dotenv import load_dotenv


load_dotenv()

guardette = Guardette()
app = FastAPI()


guardette.to_fastapi(app)
