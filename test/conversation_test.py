import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

# === 1. Init model ===
llm = ChatOpenAI(
    model_name=MODEL_NAME,
    openai_api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.7
)

# === 2. Memory container ===
memory = []

# === 3. Convert memory -> message list ===
def build_messages(user_input: str):
    messages = [SystemMessage(content="You are Lumir AI, an AI created by BEQ to help traders.")]
    for m in memory:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))
    messages.append(HumanMessage(content=user_input))
    return messages

# === 4. Chat loop ===
def chat():
    print("💬 Lumir AI is running. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye.")
            break

        # Build messages including memory
        msgs = build_messages(user_input)
        response = llm.invoke(msgs)

        # Save to memory
        memory.append({"role": "user", "content": user_input})
        memory.append({"role": "assistant", "content": response.content})

        print(f"Lumir: {response.content}\n")

# === 5. Run ===
if __name__ == "__main__":
    chat()
