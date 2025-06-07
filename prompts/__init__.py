from pathlib import Path
from langchain.prompts import PromptTemplate

with open(Path(__file__).parent / "system.md") as f:
    SYSTEM_PROMPT = PromptTemplate.from_template(f.read().strip())

with open(Path(__file__).parent / "user.md") as f:
    USER_PROMPT = PromptTemplate.from_template(f.read().strip())
