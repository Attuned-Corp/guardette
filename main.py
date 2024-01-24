from fastapi import FastAPI
from mangum import Mangum

from guardette import Guardette
from dotenv import load_dotenv


load_dotenv()

guardette = Guardette()
app = FastAPI()


guardette.to_fastapi(app)


handler = Mangum(app)
