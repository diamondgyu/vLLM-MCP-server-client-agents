import asyncio

async def async_function():
    await asyncio.sleep(1)  # Simulate an asynchronous operation
    return "Hello from async function!"

async def async_funtion2():
    await asyncio.sleep(1)  # Simulate another asynchronous operation
    return "Hello from async function 2!"

async def main():
    task1 = asyncio.create_task(async_function())
    task2 = asyncio.create_task(async_funtion2())
    results = asyncio.gather(task1, task2)
    print(results)

if __name__ == "__main__":
    asyncio.run(main())