import asyncio
import websockets.server

async def f():
    await asyncio.sleep(1)
    print(10)
    
asyncio.Queue()
async def main():
    loop = asyncio.get_event_loop()
    tasks = [asyncio.create_task(f()) for i in range(1)]
    print(asyncio.all_tasks())
    print(asyncio.ALL_COMPLETED)
if __name__ == '__main__':
    asyncio.run(main())