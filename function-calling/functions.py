from javascript import require, On, Once, AsyncTask, once, off
import asyncio
import math

# Import JavaScript modules
mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder').pathfinder
Movements = require('mineflayer-pathfinder').Movements
goals = require('mineflayer-pathfinder').goals

class MinecraftBot:
    def __init__(self, username, host='localhost', port=25565):
        self.bot = mineflayer.createBot({
            'host': host,
            'port': port,
            'username': username
        })
        
        # Load plugins
        self.bot.loadPlugin(pathfinder)
        
        # Set up event handlers
        @On(self.bot, 'spawn')
        def handle_spawn(this):
            print(f"Bot {username} spawned successfully!")
            movements = Movements(self.bot)
            self.bot.pathfinder.setMovements(movements)
    
    def move_forward(self, distance):
        """Move the bot forward by specified blocks"""
        current_pos = self.bot.entity.position
        yaw = self.bot.entity.yaw
        
        target_x = current_pos.x + distance * math.cos(yaw)
        target_z = current_pos.z + distance * math.sin(yaw)
        
        goal = goals.GoalNear(target_x, current_pos.y, target_z, 1)
        self.bot.pathfinder.setGoal(goal)
    
    def place_block(self, block_type, x_offset=0, y_offset=0, z_offset=0):
        """Place a block at relative position"""
        # Find block in inventory
        block_item = None
        for item in self.bot.inventory.items():
            if block_type.lower() in item.name.lower():
                block_item = item
                break
        
        if not block_item:
            print(f"No {block_type} found in inventory")
            return
        
        # Equip and place block
        self.bot.equip(block_item, 'hand')
        reference_block = self.bot.blockAt(self.bot.entity.position.offset(0, -1, 0))
        self.bot.placeBlock(reference_block, self.bot.Vec3(x_offset, y_offset, z_offset))
    
    def get_inventory(self):
        """Get current inventory items"""
        items = []
        for item in self.bot.inventory.items():
            items.append({
                'name': item.name,
                'count': item.count,
                'slot': item.slot
            })
        return items

# Create and run bot
bot = MinecraftBot("PythonBot")
tools = [
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
                "x_offset": {
                    "type": "number",
                    "description": "X offset from current position (default 0)"
                },
                "y_offset": {
                    "type": "number", 
                    "description": "Y offset from current position (default 0)"
                },
                "z_offset": {
                    "type": "number",
                    "description": "Z offset from current position (default 0)"
                }
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
                "x_offset": {
                    "type": "number",
                    "description": "X offset from current position"
                },
                "y_offset": {
                    "type": "number",
                    "description": "Y offset from current position"
                },
                "z_offset": {
                    "type": "number",
                    "description": "Z offset from current position"
                }
            },
            "required": ["x_offset", "y_offset", "z_offset"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "jump",
        "description": "Make the agent jump",
        "parameters": {
            "type": "object",
            "properties": {},
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
        "name": "craft_item",
        "description": "Craft an item using available materials",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "Item to craft (e.g., 'wooden_pickaxe', 'torch', 'chest')"
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of items to craft (default 1)"
                }
            },
            "required": ["item"],
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
    },
    {
        "type": "function",
        "name": "attack",
        "description": "Attack a mob or player in front of the agent",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "eat_food",
        "description": "Consume food from inventory to restore hunger",
        "parameters": {
            "type": "object",
            "properties": {
                "food_item": {
                    "type": "string",
                    "description": "Type of food to eat (e.g., 'bread', 'apple', 'cooked_beef')"
                }
            },
            "required": ["food_item"],
            "additionalProperties": False
        },
        "strict": True
    }
]