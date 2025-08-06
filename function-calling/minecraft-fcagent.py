
import asyncio
import json
import openai
from javascript import require, On, Once, AsyncTask, once, off
import math
import os

# Setup mineflayer modules
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
Movements = pathfinder.Movements
goals = pathfinder.goals

class GPTMinecraftBot:
    def __init__(self, openai_api_key, minecraft_config, model):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.minecraft_config = minecraft_config
        self.bot = None
        self.conversation_history = []
        self.model = model

        # Define available tools for function calling
        self.tools = [
            {
                "type": "function",
                "name": "move_forward",
                "description": "Move the agent forward by a specified number of blocks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "distance": {
                            "type": "number",
                            "description": "Number of blocks to move forward"
                        }
                    },
                    "required": ["distance"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "turn",
                "description": "Turn the agent left or right by specified degrees",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["left", "right"],
                            "description": "Direction to turn"
                        },
                        "degrees": {
                            "type": "number",
                            "description": "Degrees to turn (typically 90 for right angles)"
                        }
                    },
                    "required": ["direction", "degrees"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "place_block",
                "description": "Place a block at the agent's current position or relative position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "block_type": {
                            "type": "string",
                            "description": "Type of block to place (e.g., 'stone', 'dirt', 'wood')"
                        },
                        "x_offset": {"type": "number", "description": "X offset from current position (default 0)"},
                        "y_offset": {"type": "number", "description": "Y offset from current position (default 0)"},
                        "z_offset": {"type": "number", "description": "Z offset from current position (default 0)"}
                    },
                    "required": ["block_type"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "mine_block",
                "description": "Mine/break a block at the specified relative position",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x_offset": {"type": "number", "description": "X offset from current position"},
                        "y_offset": {"type": "number", "description": "Y offset from current position"},
                        "z_offset": {"type": "number", "description": "Z offset from current position"}
                    },
                    "required": ["x_offset", "y_offset", "z_offset"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "get_inventory",
                "description": "Get the current inventory items and quantities",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "look_around",
                "description": "Get information about blocks and entities in the surrounding area",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "radius": {
                            "type": "number",
                            "description": "Radius to scan around the agent (default 5)"
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                },
                "strict": True
            }
        ]

    async def initialize_bot(self):
        """Initialize the Minecraft bot connection"""
        self.bot = mineflayer.createBot(self.minecraft_config)
        self.bot.loadPlugin(pathfinder.pathfinder)

        @On(self.bot, 'spawn')
        def handle_spawn():
            print(f"Bot {self.minecraft_config['username']} spawned successfully!")
            movements = Movements(self.bot)
            self.bot.pathfinder.setMovements(movements)

        @On(self.bot, 'whisper')
        def handle_whisper(username, message, translate):
            """Handle whisper messages from players"""
            asyncio.create_task(self.process_whisper(username, message))

        @On(self.bot, 'message')
        def handle_message(jsonMsg, position):
            """Handle all chat messages to look for mentions or direct communication"""
            message = jsonMsg.toString()
            if self.minecraft_config['username'].lower() in message.lower():
                # Extract username and message content
                username = self.extract_username_from_message(jsonMsg)
                if username:
                    asyncio.create_task(self.process_message(username, message))

    async def process_whisper(self, username, message):
        """Process whisper messages using GPT and function calling"""
        print(f"Received whisper from {username}: {message}")

        try:
            # Get current game context
            context = await self.get_game_context()

            # Prepare conversation with system context
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a helpful Minecraft bot named {self.minecraft_config['username']}. 
                    You can perform various actions in the game using the available functions.
                    Current context: {context}

                    When players whisper to you, respond helpfully and use the available functions 
                    to perform actions they request. Always be conversational and explain what you're doing."""
                },
                {"role": "user", "content": f"{username} whispers: {message}"}
            ]

            # Add conversation history
            messages.extend(self.conversation_history[-10:])  # Keep last 10 messages

            # Call OpenAI API with function calling
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            # Process the response
            await self.handle_gpt_response(response, username)

        except Exception as e:
            print(f"Error processing whisper: {e}")
            self.bot.whisper(username, "Sorry, I encountered an error processing your request.")

    async def handle_gpt_response(self, response, username):
        """Handle GPT response and execute any function calls"""
        message = response.choices[0].message

        # If there are tool calls, execute them
        if message.tool_calls:
            tool_results = []

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"Executing function: {function_name} with args: {function_args}")

                try:
                    # Execute the corresponding function
                    result = await self.execute_function(function_name, function_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "result": result
                    })

                    # Send status update to user
                    self.bot.whisper(username, f"Executing: {function_name}...")

                except Exception as e:
                    error_msg = f"Error executing {function_name}: {str(e)}"
                    print(error_msg)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "result": error_msg
                    })

            # Get final response from GPT after function execution
            follow_up_messages = [message] + \
            [
                {
                    "role": "tool",
                    "tool_call_id": result["tool_call_id"],
                    "content": result["result"]
                } for result in tool_results
            ]

            final_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=follow_up_messages,
                tools=self.tools
            )

            final_message = final_response.choices[0].message.content
            if final_message:
                self.bot.whisper(username, final_message)

        # If there's a direct text response
        elif message.content:
            self.bot.whisper(username, message.content)

    async def execute_function(self, function_name, args):
        """Execute the specified function with given arguments"""
        if function_name == "move_forward":
            return await self.move_forward(args["distance"])
        elif function_name == "turn":
            return await self.turn(args["direction"], args["degrees"])
        elif function_name == "place_block":
            return await self.place_block(
                args["block_type"],
                args.get("x_offset", 0),
                args.get("y_offset", 0),
                args.get("z_offset", 0)
            )
        elif function_name == "mine_block":
            return await self.mine_block(args["x_offset"], args["y_offset"], args["z_offset"])
        elif function_name == "get_inventory":
            return await self.get_inventory()
        elif function_name == "look_around":
            return await self.look_around(args.get("radius", 5))
        else:
            raise ValueError(f"Unknown function: {function_name}")

    # Minecraft action functions
    async def move_forward(self, distance):
        """Move the bot forward by specified distance"""
        current_pos = self.bot.entity.position
        yaw = self.bot.entity.yaw

        target_x = current_pos.x + distance * math.cos(yaw)
        target_z = current_pos.z + distance * math.sin(yaw)

        goal = goals.GoalNear(target_x, current_pos.y, target_z, 1)
        self.bot.pathfinder.setGoal(goal)

        # Wait for movement to complete
        await self.wait_for_goal_reached()
        return f"Moved forward {distance} blocks"

    async def turn(self, direction, degrees):
        """Turn the bot left or right"""
        current_yaw = self.bot.entity.yaw
        radians = math.radians(degrees)

        if direction == 'left':
            new_yaw = current_yaw - radians
        else:
            new_yaw = current_yaw + radians

        await self.bot.look(new_yaw, self.bot.entity.pitch, False)
        return f"Turned {direction} {degrees} degrees"

    async def place_block(self, block_type, x_offset=0, y_offset=0, z_offset=0):
        """Place a block at the specified offset"""
        # Find block in inventory
        block_item = self.find_inventory_item(block_type)
        if not block_item:
            return f"No {block_type} blocks in inventory"

        # Equip and place block
        await self.bot.equip(block_item, 'hand')
        reference_block = self.bot.blockAt(self.bot.entity.position.offset(0, -1, 0))
        await self.bot.placeBlock(reference_block, self.bot.Vec3(x_offset, y_offset, z_offset))

        return f"Placed {block_type} block at offset ({x_offset}, {y_offset}, {z_offset})"

    async def mine_block(self, x_offset, y_offset, z_offset):
        """Mine a block at the specified offset"""
        target_pos = self.bot.entity.position.offset(x_offset, y_offset, z_offset)
        block = self.bot.blockAt(target_pos)

        if not block or block.name == 'air':
            return f"No block to mine at offset ({x_offset}, {y_offset}, {z_offset})"

        await self.bot.dig(block)
        return f"Mined {block.name} at offset ({x_offset}, {y_offset}, {z_offset})"

    async def get_inventory(self):
        """Get current inventory items"""
        items = []
        for item in self.bot.inventory.items():
            items.append({
                'name': item.name,
                'count': item.count,
                'slot': item.slot
            })
        return json.dumps(items)

    async def look_around(self, radius=5):
        """Look around and report nearby blocks and entities"""
        blocks = []
        entities = []
        current_pos = self.bot.entity.position

        # Scan for blocks
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                for z in range(-radius, radius + 1):
                    block = self.bot.blockAt(current_pos.offset(x, y, z))
                    if block and block.name != 'air':
                        blocks.append({'name': block.name, 'position': (x, y, z)})

        # Find nearby entities
        for entity in self.bot.entities.values():
            if entity != self.bot.entity:
                distance = current_pos.distanceTo(entity.position)
                if distance <= radius:
                    entities.append({
                        'name': entity.name or 'unknown',
                        'type': entity.type,
                        'distance': round(distance, 2)
                    })

        return json.dumps({'blocks': blocks[:20], 'entities': entities})

    async def get_game_context(self):
        """Get current game context for GPT"""
        pos = self.bot.entity.position
        health = self.bot.health
        food = self.bot.food

        context = {
            'position': {'x': round(pos.x), 'y': round(pos.y), 'z': round(pos.z)},
            'health': health,
            'food': food,
            'time': self.bot.time.timeOfDay,
            'weather': 'clear'  # Would need to implement weather detection
        }
        return json.dumps(context)

    def find_inventory_item(self, item_name):
        """Find an item in the bot's inventory"""
        for item in self.bot.inventory.items():
            if item_name.lower() in item.name.lower():
                return item
        return None

    async def wait_for_goal_reached(self):
        """Wait for pathfinder to reach goal"""
        future = asyncio.get_event_loop().create_future()

        def on_goal_reached():
            if not future.done():
                future.set_result(True)

        def on_path_timeout():
            if not future.done():
                future.set_exception(Exception("Pathfinding timeout"))

        self.bot.once('goal_reached', on_goal_reached)
        self.bot.once('path_timeout', on_path_timeout)

        await future

    def extract_username_from_message(self, json_msg):
        """Extract username from message JSON"""
        # Implementation would depend on message format
        # This is a simplified version
        return "player"  # Placeholder

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

    await bot.initialize_bot()

    # Keep the bot running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
