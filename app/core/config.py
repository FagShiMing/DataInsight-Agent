import os
from dotenv import load_dotenv

load_dotenv()

ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
ZHIPUAI_MODEL = os.getenv("ZHIPUAI_MODEL", "glm-4.7")