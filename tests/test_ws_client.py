import asyncio
import json
import websockets


async def test_websocket():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {uri}", flush=True)

        # Authenticate
        auth_msg = {"action": "auth", "api_key": "dev_secret_key"}
        await websocket.send(json.dumps(auth_msg))
        print(f"Sent auth: {auth_msg}", flush=True)

        # Subscribe
        sub_msg = {
            "action": "subscribe",
            "symbols": [
                {"symbol": "NIFTY 50", "exchange": "NSE"},
                {"symbol": "BANKNIFTY", "exchange": "NSE"},
            ],
            "mode": "LTP",
        }
        await websocket.send(json.dumps(sub_msg))
        print(f"Sent subscribe: {sub_msg}", flush=True)

        # Listen for messages
        try:
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received: {data}", flush=True)

                if data.get("type") == "market_data":
                    print("SUCCESS: Received market data!", flush=True)
                    break
        except Exception as e:
            print(f"Error: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(test_websocket())
