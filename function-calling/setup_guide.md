
# GPT Minecraft Bot Setup Guide

## Prerequisites

1. **Node.js** (version 14 or higher)
2. **Python** (version 3.8 or higher)
3. **Minecraft Java Edition** server
4. **OpenAI API Key**

## Installation Steps

### 1. Install Node.js Dependencies

```bash
npm install mineflayer mineflayer-pathfinder minecraft-data
```

### 2. Install Python Dependencies

```bash
pip install openai asyncio javascript
```

### 3. Environment Setup

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
MINECRAFT_HOST=localhost
MINECRAFT_PORT=25565
MINECRAFT_USERNAME=GPTBot
MINECRAFT_VERSION=1.20.1
```

### 4. JavaScript Bridge Setup

Since Mineflayer is a JavaScript library, you'll need to use a JavaScript-Python bridge.
Install the `javascript` package for Python:

```bash
pip install javascript
```

Alternative approach using subprocess:

```python
# If the javascript bridge doesn't work, you can use subprocess to run Node.js
import subprocess
import json

def run_minecraft_action(action, params):
    script = f"""
    const mineflayer = require('mineflayer');
    const bot = mineflayer.createBot({{
        host: '{process.env.MINECRAFT_HOST}',
        port: {process.env.MINECRAFT_PORT},
        username: '{process.env.MINECRAFT_USERNAME}'
    }});

    // Implement action here
    console.log(JSON.stringify({{success: true, result: 'Action completed'}}));
    """

    result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    return json.loads(result.stdout)
```

## Configuration

### Minecraft Server Setup

1. Start your Minecraft server
2. Ensure the bot can connect (whitelist if necessary)
3. Make sure whisper/tell commands are enabled

### OpenAI API Setup

1. Get your API key from https://platform.openai.com/
2. Add it to your environment variables
3. Ensure you have credits available

## Running the Bot

```bash
python gpt_minecraft_bot.py
```

## How It Works

1. **Player sends whisper**: `/tell GPTBot build me a house`
2. **Bot receives whisper**: Captured by event handler
3. **GPT processing**: Message sent to OpenAI with function calling tools
4. **Function execution**: GPT decides which Minecraft functions to call
5. **Action performed**: Bot executes the actions in Minecraft
6. **Response**: Bot whispers back the results

## Example Commands Players Can Use

- `/tell GPTBot move forward 5 blocks`
- `/tell GPTBot turn left 90 degrees`
- `/tell GPTBot place a stone block in front of me`
- `/tell GPTBot what's in your inventory?`
- `/tell GPTBot look around and tell me what you see`
- `/tell GPTBot mine the block above you`

## Troubleshooting

### Common Issues

1. **Bot won't connect**: Check server settings and credentials
2. **Function calls not working**: Verify OpenAI API key and model access
3. **JavaScript bridge errors**: Try the subprocess approach instead

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Alternative Pure Python Approach

If the JavaScript bridge is problematic, you can use a pure Python approach:

```python
# Using pyCraft for pure Python implementation
from minecraft import authentication
from minecraft.networking.connection import Connection
from minecraft.networking.packets import clientbound, serverbound

# This approach requires more low-level implementation
# but avoids JavaScript dependencies
```

## Security Considerations

1. **API Key Protection**: Never commit API keys to version control
2. **Rate Limiting**: Implement rate limiting for whisper commands
3. **Command Filtering**: Filter inappropriate requests before sending to GPT
4. **Server Permissions**: Run bot with minimal required permissions

## Extending the Bot

### Adding New Functions

1. Add function definition to `self.tools` array
2. Implement the function in `execute_function` method
3. Add the actual Minecraft logic

### Custom Responses

Modify the system prompt to change bot personality:

```python
system_content = """You are a medieval knight bot in Minecraft. 
Speak in ye olde English and be chivalrous in your responses."""
```
