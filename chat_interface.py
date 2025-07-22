import chainlit as cl
from engine.langgraph_engine import run_engine
import os

conversation_history = []

@cl.on_message
async def on_message(message: cl.Message):
    conversation_history.append({"role": "user", "content": message.content})

    # Run engine
    result, context = await run_engine(message.content, conversation_history)
    conversation_history.append({"role": "assistant", "content": result})

    # Send main response message
    await cl.Message(content=result).send()

    # Check and send multiple image paths if present
    image_paths = context.get("dashboard_screenshot_paths", [])
    if isinstance(image_paths, str):  # convert single string to list
        image_paths = [image_paths]

    for image_path in image_paths:
        if image_path and os.path.exists(image_path):
            await cl.Image(name=os.path.basename(image_path), path=image_path, display="inline").send()