const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');

// Assuming bot is already created and connected
// const bot = mineflayer.createBot({ ... })

function move_forward(distance) {
    return new Promise((resolve, reject) => {
        const movements = new Movements(bot);
        bot.pathfinder.setMovements(movements);
        
        const currentPos = bot.entity.position;
        const yaw = bot.entity.yaw;
        
        const targetX = currentPos.x + Math.cos(yaw) * distance;
        const targetZ = currentPos.z + Math.sin(yaw) * distance;
        
        const goal = new goals.GoalNear(targetX, currentPos.y, targetZ, 1);
        
        bot.pathfinder.setGoal(goal);
        
        bot.once('goal_reached', () => {
            resolve(`Moved forward ${distance} blocks`);
        });
        
        bot.once('path_timeout', () => {
            reject(new Error('Failed to move forward - path timeout'));
        });
    });
}

function turn(direction, degrees) {
    return new Promise((resolve) => {
        const currentYaw = bot.entity.yaw;
        const radians = (degrees * Math.PI) / 180;
        const newYaw = direction === 'left' ? currentYaw - radians : currentYaw + radians;
        
        bot.look(newYaw, bot.entity.pitch, false);
        resolve(`Turned ${direction} ${degrees} degrees`);
    });
}

function place_block(block_type, x_offset = 0, y_offset = 0, z_offset = 0) {
    return new Promise((resolve, reject) => {
        const currentPos = bot.entity.position;
        const targetPos = {
            x: Math.floor(currentPos.x + x_offset),
            y: Math.floor(currentPos.y + y_offset),
            z: Math.floor(currentPos.z + z_offset)
        };
        
        const blockItem = bot.inventory.items().find(item => 
            item.name.includes(block_type) || item.displayName.toLowerCase().includes(block_type.toLowerCase())
        );
        
        if (!blockItem) {
            reject(new Error(`No ${block_type} blocks in inventory`));
            return;
        }
        
        bot.equip(blockItem, 'hand').then(() => {
            const referenceBlock = bot.blockAt(bot.entity.position.offset(0, -1, 0));
            bot.placeBlock(referenceBlock, new bot.Vec3(x_offset, y_offset, z_offset))
                .then(() => resolve(`Placed ${block_type} block at offset (${x_offset}, ${y_offset}, ${z_offset})`))
                .catch(reject);
        }).catch(reject);
    });
}

function mine_block(x_offset, y_offset, z_offset) {
    return new Promise((resolve, reject) => {
        const currentPos = bot.entity.position;
        const targetBlock = bot.blockAt({
            x: Math.floor(currentPos.x + x_offset),
            y: Math.floor(currentPos.y + y_offset),
            z: Math.floor(currentPos.z + z_offset)
        });
        
        if (!targetBlock || targetBlock.name === 'air') {
            reject(new Error('No block to mine at specified position'));
            return;
        }
        
        bot.dig(targetBlock)
            .then(() => resolve(`Mined ${targetBlock.name} at offset (${x_offset}, ${y_offset}, ${z_offset})`))
            .catch(reject);
    });
}

function jump() {
    return new Promise((resolve) => {
        bot.setControlState('jump', true);
        setTimeout(() => {
            bot.setControlState('jump', false);
            resolve('Jumped');
        }, 100);
    });
}

function get_inventory() {
    return new Promise((resolve) => {
        const inventory = bot.inventory.items().map(item => ({
            name: item.name,
            displayName: item.displayName,
            count: item.count,
            slot: item.slot
        }));
        resolve(JSON.stringify(inventory, null, 2));
    });
}

function craft_item(item, quantity = 1) {
    return new Promise((resolve, reject) => {
        const mcData = require('minecraft-data')(bot.version);
        const recipe = bot.recipesFor(mcData.itemsByName[item]?.id, null, 1, null)[0];
        
        if (!recipe) {
            reject(new Error(`No recipe found for ${item}`));
            return;
        }
        
        bot.craft(recipe, quantity)
            .then(() => resolve(`Crafted ${quantity} ${item}(s)`))
            .catch(reject);
    });
}

function look_around(radius = 5) {
    return new Promise((resolve) => {
        const currentPos = bot.entity.position;
        const blocks = [];
        const entities = [];
        
        // Scan blocks in radius
        for (let x = -radius; x <= radius; x++) {
            for (let y = -radius; y <= radius; y++) {
                for (let z = -radius; z <= radius; z++) {
                    const block = bot.blockAt({
                        x: Math.floor(currentPos.x + x),
                        y: Math.floor(currentPos.y + y),
                        z: Math.floor(currentPos.z + z)
                    });
                    
                    if (block && block.name !== 'air') {
                        blocks.push({
                            name: block.name,
                            position: { x: x, y: y, z: z }
                        });
                    }
                }
            }
        }
        
        // Get nearby entities
        Object.values(bot.entities).forEach(entity => {
            const distance = currentPos.distanceTo(entity.position);
            if (distance <= radius && entity !== bot.entity) {
                entities.push({
                    name: entity.name || entity.displayName || 'unknown',
                    type: entity.type,
                    distance: Math.round(distance * 100) / 100,
                    position: entity.position
                });
            }
        });
        
        resolve(JSON.stringify({ blocks: blocks.slice(0, 20), entities }, null, 2));
    });
}

function attack() {
    return new Promise((resolve, reject) => {
        const target = bot.nearestEntity(entity => 
            entity.type === 'mob' && 
            bot.entity.position.distanceTo(entity.position) < 4
        );
        
        if (!target) {
            reject(new Error('No target found to attack'));
            return;
        }
        
        bot.attack(target);
        resolve(`Attacked ${target.name || target.displayName || 'entity'}`);
    });
}

function eat_food(food_item) {
    return new Promise((resolve, reject) => {
        const foodItem = bot.inventory.items().find(item => 
            item.name.includes(food_item) || item.displayName.toLowerCase().includes(food_item.toLowerCase())
        );
        
        if (!foodItem) {
            reject(new Error(`No ${food_item} found in inventory`));
            return;
        }
        
        bot.equip(foodItem, 'hand').then(() => {
            bot.consume();
            resolve(`Ate ${food_item}`);
        }).catch(reject);
    });
}

// Export all functions
module.exports = {
    move_forward,
    turn,
    place_block,
    mine_block,
    jump,
    get_inventory,
    craft_item,
    look_around,
    attack,
    eat_food
};