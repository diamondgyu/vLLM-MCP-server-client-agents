from openai import OpenAI

from functions import add_two_nums
import json

client = OpenAI()

tools = [{
    "type": "function",
    "name": "add_two_nums",
    "description": "add two numbers",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {
                "type": "number",
                "description": "The first number to add"
            },
            "y": {
                "type": "number",
                "description": "The second number to add"
            }
        },
        "required": ['x', 'y'],
        "additionalProperties": False
    },
    "strict": True
}]

input_messages = [{"role": "user", "content": "suggest a city that has longitide value of 5 plus 120. call add_two_nums with the two numbers"}]

response = client.responses.create(
    model="gpt-4o-mini",
    input=input_messages,
    tools=tools,
)

# print(response.output)

print(response.output)
print(response.output_text)

call_info = response.output[0]
args = json.loads(call_info.arguments)
if call_info.name == "add_two_nums":
    result = add_two_nums(**args)
else:
    print(f"Unknown function: {response.output['name']}")

input_messages.append(call_info)  # append model's function call message
input_messages.append({                               # append result message
    "type": "function_call_output",
    "call_id": call_info.call_id,
    "output": str(result)
})

response_2 = client.responses.create(
    model="gpt-4.1",
    input=input_messages,
    tools=tools,
)

print("Final output:", response_2.output_text)