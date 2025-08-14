import asyncio
import json
import queue
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Callable
from openai import OpenAI
from tools import mineflayer_tools
import traceback

# -----------------------------
# Data models
# -----------------------------
@dataclass
class WhisperMessage:
    username: str
    message: str
    timestamp: float

# A simplified view of OpenAI Responses SDK result units
@dataclass
class ResponseOutputMessage:
    role: str
    content: List[Any]  # usually list of Text or ToolCall
    # Optional metadata / extra fields can be added as needed

# -----------------------------
# Delegation primitives
# -----------------------------
@dataclass
class DelegatedTask:
    id: str
    description: str
    status: str  # pending, running, done, failed
    result: Optional[Dict[str, Any]] = None
    assigned_agent: Optional[str] = None  # e.g., "builder", "miner"


class WhisperMessageProcessor:
    def __init__(self, openai_client: OpenAI, minecraft_bot, GoalNear, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.bot = minecraft_bot
        self.model = model
        self.whisper_queue: "queue.Queue[WhisperMessage]" = queue.Queue()
        self.running = False
        self.processor_task: Optional[asyncio.Task] = None
        self.GoalNear = GoalNear  # Used for pathfinding goals

        # Task delegation queues and state
        self.delegated_tasks: Dict[str, DelegatedTask] = {}
        self.delegate_handlers: Dict[str, Callable[[DelegatedTask], asyncio.Task]] = {
            # Example: "miner": self._delegate_to_miner, "builder": self._delegate_to_builder
        }

    # -----------------------------
    # Public API
    # -----------------------------
    def add_whisper(self, username: str, message: str):
        whisper_msg = WhisperMessage(
            username=username,
            message=message,
            timestamp=asyncio.get_event_loop().time() if asyncio._get_running_loop() else 0.0
        )
        self.whisper_queue.put(whisper_msg)
        print(f"Added whisper from {username}: {message}")

    def start_processing(self):
        if self.running:
            print("Whisper processor already running")
            return
        self.running = True
        self.processor_task = asyncio.create_task(self._process_loop())
        print("Whisper message processor started")

    def stop_processing(self):
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
        print("Whisper message processor stopped")

    async def _process_loop(self):
        while self.running:
            whisper_msg = await self._get_next_whisper()
            if not whisper_msg:
                await asyncio.sleep(0.1)
                continue
            print("Processing whisper:", whisper_msg)
            await self._process_whisper_message(whisper_msg)
            await asyncio.sleep(0.1)

    async def _get_next_whisper(self) -> Optional[WhisperMessage]:
        try:
            return self.whisper_queue.get_nowait()
        except queue.Empty:
            return None

    # -----------------------------
    # Core GPT workflow per whisper
    # -----------------------------
    async def _process_whisper_message(self, whisper_msg: WhisperMessage):
        print(f"Processing whisper from {whisper_msg.username}: {whisper_msg.message}")
        conversation: List[Dict[str, Union[str, Any]]] = [
            {
                "role": "system",
                "content": (
                    "You are a Minecraft bot assistant. You can perform actions in Minecraft "
                    "using function calls. When a user asks you to do something, use the appropriate "
                    "functions to accomplish their request. If they're just talking, respond normally. "
                    "Always give the absolute coordinate values for arguments. If you need relative ones, "
                    "first query the current absolute coordinates and then calculate the relative ones. "
                    "If more steps are needed after a function call, concisely state the next steps. "
                    "If the task is large or long-running, you may delegate subtasks to specialized agents "
                    "and mark this conversation pending until delegated tasks complete. Prefer delegation "
                    "when the whisper queue is not empty."
                    "If you need a reply based on the function call result, explicitly say it by response message"
                    "Never use markdown formatting in your responses. "
                    "Always use whisper function to send message to the user."
                )
            },
            {
                "role": "user",
                "content": f"Message from {whisper_msg.username}: {whisper_msg.message}"
            },
            {
                "role": "system",
                "content": f"Game context: {self.get_game_context()}"
            }
        ]

        await self._handle_gpt_conversation(conversation, whisper_msg)

    async def _handle_gpt_conversation(self, conversation: List[Dict], whisper_msg: WhisperMessage):
        max_iterations = 10
        iteration = 0

        try:

            while iteration < max_iterations:
                print("\n" + "-" * 70 + "\n")
                print(f"Conversation #{iteration+1}:", conversation)

                response_units = await self._send_to_gpt(conversation)
                if not response_units:
                    break
                
                print('\nResponses: ', response_units)

                for unit in response_units:

                    # If plain text assistant message
                    if hasattr(unit, 'content'):
                        final_text = unit.content[0].text.replace("\n", " ").strip() if unit.content else str(unit)
                        self.bot.whisper(whisper_msg.username, final_text)
                        conversation.append({"role": "assistant", "content": final_text})
                        print('\nSent response to user:', final_text)
                        continue

                    # Otherwise treat as tool/function call unit following OpenAI Responses API schema
                    tool_calls = []
                    if hasattr(unit, "type") and getattr(unit, "type") == "function_call":
                        tool_calls = [unit]
                    else:
                        raise ValueError(f"Unexpected response unit type: {type(unit)}. Expected function call or text message.")

                    # Execute requested tool calls
                    print(f"\nExecuting tool calls: {tool_calls}")
                    function_results = await self._execute_function_calls(tool_calls)

                    # Append status summary to conversation
                    if function_results:
                        # Summarize single call result status or short JSON
                        summary = function_results[0].get("status") or json.dumps(function_results[0])[:500]
                        conversation.append({"role": "assistant", "content": str(function_results)})
                        print("done with this function call\n")
                
                if hasattr(response_units[-1], 'content'):
                    # If the last response was a text message, we can stop here
                    break

                if response_units[-1].name == 'whisper':
                    break

                iteration += 1
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error processing whisper from {whisper_msg.username}: {e}")
            traceback.print_exc()

    async def _send_to_gpt(self, conversation: List[Dict]) -> Optional[Any]:
        # Using the Responses API with tool calling
        # Note: For some SDK versions, messages field is `input`, and tools go in `tools`.
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.responses.create(
                model=self.model,
                input=conversation,
                tools=mineflayer_tools,
                tool_choice="auto"
            )
        )
        # The SDK returns response.output as a list of units (messages/tool calls)
        return getattr(response, "output", None)

    async def _execute_function_calls(self, tool_calls) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for call in tool_calls:
            # Normalize fields
            function_name = getattr(call, "name", None) or getattr(call, "tool_name", None)
            raw_args = getattr(call, "arguments", "{}")
            if not function_name:
                results.append({"error": "Missing function name"})
                continue

            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                arguments = {}
            print(f"\nExecuting function: {function_name} with args: {arguments}")
        
            result = await self.handle_function_call(function_name, arguments)
            results.append(result)
            print(f"\nFunction {function_name} result: {result}")

        return results

    def get_queue_size(self) -> int:
        return self.whisper_queue.qsize()

    def is_running(self) -> bool:
        return self.running

    # -----------------------------
    # Main function call handler
    # This is the adapter layer between GPT tool calls and the actual mineflayer bot API.
    # It assumes `self.bot` exposes async methods compatible with the below signatures.
    # If not, wrap callbacks or sync methods into asyncio with run_in_executor.
    # -----------------------------
    async def handle_function_call(self, function_name, parameters):
        # World Info
        try:
            
            if function_name == "whisper":
                return self.whisper(parameters)
            elif function_name == 'move_to':
                return self.move_to(parameters)

            else:
                return {"error": f"Unknown function: {function_name}"}
            
        except Exception as e:
            print(f"Error executing function {function_name} with params {parameters}: {e}")
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
        
    # -----------------------------
    # Helper to expose current context
    # -----------------------------
    def get_game_context(self):
        pos = self.bot.entity.position
        health = getattr(self.bot, "health", None)
        food = getattr(self.bot, "food", None)
        time_of_day = getattr(getattr(self.bot, "time", None), "timeOfDay", None)
        context = {
            "position": {"x": round(pos.x), "y": round(pos.y), "z": round(pos.z)},
            "health": health,
            "food": food,
            "time": time_of_day,
            "weather": "clear"  # placeholder unless weather detection is implemented
        }
        return json.dumps(context)
    
    def whisper(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Send a whisper message to a player."""
        username = parameters.get("username")
        message = parameters.get("message")
        if not username or not message:
            return {"status": "error", "error": "Missing username or message"}
        
        self.bot.whisper(username, message)
        return {"status": "success", "message": f"Whispered to {username}: {message}"}

    def move_to(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Move the bot to a specific position in the world."""
        x = parameters.get("x")
        y = parameters.get("y")
        z = parameters.get("z")
        if x is None or y is None or z is None:
            return {"status": "error", "error": "Missing x, y, or z coordinates"}

        try:
            self.bot.pathfinder.setGoal(self.GoalNear(x, y, z, 1))  # 1 block radius tolerance
            return {"status": "success", "message": f"Moving to ({x}, {y}, {z})"}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "error": str(e)}