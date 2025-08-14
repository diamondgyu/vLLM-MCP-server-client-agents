from agents import Agent, FunctionTool, Runner, function_tool, RunConfig
import json

@function_tool
async def get_latest_news():
    # This function would typically fetch the latest news from an API or database.
    # For demonstration purposes, we'll return a static message.
    return "Latest news: Major breakthrough in AI technology announced today."

@function_tool
async def create_new_team(team_name: str, team_members: list):
    # This function would typically create a new team in a database or system.
    # For demonstration purposes, we'll return a success message.
    return f"Team '{team_name}' created with members: {', '.join(team_members)}."

news_agent = Agent(
    name="NewsAgent",
    instructions="You are a news agent that provides the latest news updates. Respond with concise and relevant news summaries.",
    tools=[get_latest_news, create_new_team],
)

def main():
    # Simulate the agent being called to get the latest news

    result = Runner.run_sync(
        starting_agent=news_agent,
        run_config=RunConfig(model="gpt-4o-mini"),
        input="What is the latest news?"
    )
    print("Agent Response:", result.final_output)

if __name__ == "__main__":
    main()