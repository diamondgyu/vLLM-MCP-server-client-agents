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
    
    async def move_forward(self, distance):
        """Move the agent forward by a specified number of blocks"""
        current_pos = self.bot.entity.position
        yaw = self.bot.entity.yaw
        
        # Calculate target position based on current facing direction
        target_x = current_pos.x + distance * math.cos(yaw)
        target_z = current_pos.z + distance * math.sin(yaw)
        target_y = current_pos.y
        
        # Use pathfinder to move to target
        goal = self.bot.goals.GoalNear(target_x, target_y, target_z, 1)
        self.bot.pathfinder.setGoal(goal)
        await self._wait_for_goal_reached()
        return f"Moved forward {distance} blocks"

    async def turn(self, direction, degrees):
        """Turn the agent left or right by specified degrees"""
        current_yaw = self.bot.entity.yaw
        radians = math.radians(degrees)
        
        if direction == 'left':
            new_yaw = current_yaw - radians
        else:  # right
            new_yaw = current_yaw + radians
        
        await self.bot.look(new_yaw, self.bot.entity.pitch, False)
        return f"Turned {direction} {degrees} degrees"

    async def place_block(self, block_type, x_offset=0, y_offset=0, z_offset=0):
        """Place a block at the agent's current position or relative position"""
        # Find the block in inventory
        block_item = self._find_inventory_item(block_type)
        if not block_item:
            raise Exception(f"No {block_type} block in inventory")
        
        # Equip the block
        await self.bot.equip(block_item, 'hand')
        
        # Place the block at the specified offset
        current_pos = self.bot.entity.position
        target_pos = current_pos.offset(x_offset, y_offset, z_offset)
        reference_block = self.bot.blockAt(current_pos.offset(0, -1, 0))
        
        await self.bot.placeBlock(reference_block, self.bot.Vec3(x_offset, y_offset, z_offset))
        return f"Placed {block_type} block at offset ({x_offset}, {y_offset}, {z_offset})"

    async def mine_block(self, x_offset, y_offset, z_offset):
        """Mine/break a block at the specified relative position"""
        current_pos = self.bot.entity.position
        target_pos = current_pos.offset(x_offset, y_offset, z_offset)
        block = self.bot.blockAt(target_pos)
        
        if not block or block.name == 'air':
            raise Exception(f"No block to mine at offset ({x_offset}, {y_offset}, {z_offset})")
        
        await self.bot.dig(block)
        return f"Mined {block.name} at offset ({x_offset}, {y_offset}, {z_offset})"

    async def jump(self):
        """Make the agent jump"""
        self.bot.setControlState('jump', True)
        await asyncio.sleep(0.2)  # Hold jump for 200ms
        self.bot.setControlState('jump', False)
        return "Jumped"

    async def get_inventory(self):
        """Get the current inventory items and quantities"""
        inventory = []
        for item in self.bot.inventory.items():
            inventory.append({
                'name': item.name,
                'displayName': item.displayName,
                'count': item.count,
                'slot': item.slot
            })
        return inventory

    async def craft_item(self, item, quantity=1):
        """Craft an item using available materials"""
        mcData = self.bot.mcData
        item_data = mcData.itemsByName.get(item)
        
        if not item_data:
            raise Exception(f"Item not found: {item}")
        
        # Find recipes for the item
        recipes = self.bot.recipesFor(item_data.id, None, 1, None)
        if not recipes:
            raise Exception(f"No recipes found for {item}")
        
        recipe = recipes[0]
        await self.bot.craft(recipe, quantity)
        return f"Crafted {quantity} {item}(s)"

    async def look_around(self, radius=5):
        """Get information about blocks and entities in the surrounding area"""
        blocks = []
        entities = []
        current_pos = self.bot.entity.position
        
        # Scan for blocks in radius
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                for z in range(-radius, radius + 1):
                    block = self.bot.blockAt(current_pos.offset(x, y, z))
                    if block and block.name != 'air':
                        blocks.append({
                            'name': block.name,
                            'position': {'x': x, 'y': y, 'z': z}
                        })
        
        # Find nearby entities
        for entity in self.bot.entities.values():
            if entity != self.bot.entity:
                distance = current_pos.distanceTo(entity.position)
                if distance <= radius:
                    entities.append({
                        'name': entity.name or entity.displayName or 'unknown',
                        'type': entity.type,
                        'distance': round(distance, 2),
                        'position': {
                            'x': entity.position.x,
                            'y': entity.position.y,
                            'z': entity.position.z
                        }
                    })
        
        return {
            'blocks': blocks[:50],  # Limit to prevent overwhelming output
            'entities': entities
        }

    async def attack(self):
        """Attack a mob or player in front of the agent"""
        current_pos = self.bot.entity.position
        target = None
        
        # Find nearest hostile mob within attack range
        for entity in self.bot.entities.values():
            if entity == self.bot.entity:
                continue
            
            distance = current_pos.distanceTo(entity.position)
            if distance < 4 and entity.type == 'mob':
                target = entity
                break
        
        if not target:
            raise Exception('No mob found to attack within range')
        
        await self.bot.attack(target)
        return f"Attacked {target.name or target.displayName or 'entity'}"

    async def eat_food(self, food_item):
        """Consume food from inventory to restore hunger"""
        # Find food item in inventory
        food = self._find_inventory_item(food_item)
        if not food:
            raise Exception(f"No {food_item} found in inventory")
        
        # Equip and consume the food
        await self.bot.equip(food, 'hand')
        await self.bot.consume()
        return f"Ate {food_item}"

    # Helper methods
    def _find_inventory_item(self, item_name):
        """Helper method to find an item in the bot's inventory"""
        for item in self.bot.inventory.items():
            if (item_name.lower() in item.name.lower() or 
                item_name.lower() in item.displayName.lower()):
                return item
        return None

    async def _wait_for_goal_reached(self):
        """Helper method to wait for pathfinding goal to be reached"""
        future = asyncio.get_event_loop().create_future()
        
        def on_goal_reached():
            if not future.done():
                future.set_result(True)
        
        def on_path_timeout():
            if not future.done():
                future.set_exception(Exception("Pathfinding timeout"))
        
        # Register event listeners
        self.bot.once('goal_reached', on_goal_reached)
        self.bot.once('path_timeout', on_path_timeout)
        
        try:
            await future
        finally:
            # Clean up event listeners
            self.bot.removeListener('goal_reached', on_goal_reached)
            self.bot.removeListener('path_timeout', on_path_timeout)

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