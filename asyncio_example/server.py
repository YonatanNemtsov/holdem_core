import asyncio
import websockets.server

async def f():
    await asyncio.sleep(1)
    print(10)
    
asyncio.Queue()
async def main():
    loop = asyncio.get_event_loop()
    tasks = [asyncio.create_task(f()) for i in range(100)]

if __name__ == '__main__':
    asyncio.run(main())
    