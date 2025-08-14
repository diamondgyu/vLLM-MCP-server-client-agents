# -----------------------------
# Mineflayer tool schema (tool definitions for function calling)
# These should mirror the mineflayer/mineflayer plugin methods that your Python bridge can execute.
# If calling Node/JS mineflayer behind the scenes, ensure your bridge layer exposes these methods.
# -----------------------------
mineflayer_tools = [
    {
        "type": "function",
        "name": "whisper",
        "description": "Send a private whisper to a player",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["username", "message"]
        }
    },
    {
        "type": "function",
        "name": "chat",
        "description": "Send a message to the global chat",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }
    },
    # move bot to position x, y, z
    {
        "type": "function",
        "name": "move_to",
        "description": "Move the bot to a specific position in the world",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "z": {"type": "number"}
            },
            "required": ["x", "y", "z"]
        }
    },
]