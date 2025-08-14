
import asyncio
import json
from openai.types.responses import ResponseOutputMessage
from openai import OpenAI
from javascript import require, On, Once, AsyncTask, once, off
import os
import traceback
from threading import Thread
from collections import deque

from tools import mineflayer_tools
from WhisperProcessor import WhisperMessageProcessor

# Setup mineflayer modules
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')

Movements = pathfinder.Movements
goals = pathfinder.goals
GoalNear = goals.GoalNear
# -----------------------------

class GPTMinecraftBot:
    def __init__(self, openai_api_key, minecraft_config, model):
        self.minecraft_config = minecraft_config
        self.bot = None
        self.conversation_history = []

        """Initialize the Minecraft bot connection"""
        self.bot = mineflayer.createBot(self.minecraft_config)
        self.bot.loadPlugin(pathfinder.pathfinder)

        @On(self.bot, 'spawn')
        def handle_spawn(bot):
            print(f"Bot {self.minecraft_config['username']} spawned successfully!")
            movements = Movements(self.bot)
            self.bot.pathfinder.setMovements(movements)

        @On(self.bot, 'whisper')
        def handle_whisper(bot, username, message, translate, verified):
            """Handle whisper messages from players"""
            self.processor.add_whisper(username, message)

        self.processor = WhisperMessageProcessor(
            OpenAI(api_key=openai_api_key),
            self.bot,
            GoalNear,
            model
        )

        self.processor.start_processing()

# Usage example
async def main():
    config = {
        'host': 'localhost',
        'port': 25565,
        'username': 'GPTBot',
        'version': '1.21.1'
    }

    bot = GPTMinecraftBot(
        openai_api_key=os.environ.get('OPENAI_API_KEY'),
        minecraft_config=config,
        model="gpt-4o-mini"
    )

    # Keep the bot running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
