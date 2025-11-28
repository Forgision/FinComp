import asyncio
import json
import random
import zmq
import zmq.asyncio
from app.core.config import settings


class DataService:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.rep_socket = self.context.socket(zmq.REP)
        self.pub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}"
        self.rep_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}"
        self.running = False
        self.subscribed_symbols = set()

    async def start(self):
        print(f"Binding PUB socket to {self.pub_address}")
        print(f"Binding REP socket to {self.rep_address}")
        try:
            self.pub_socket.bind(self.pub_address)
            self.rep_socket.bind(self.rep_address)
        except zmq.error.ZMQError as e:
            print(f"Failed to bind sockets: {e}")
            return

        self.running = True
        await asyncio.gather(self.produce_data(), self.handle_requests())

    async def handle_requests(self):
        print("Starting request handler...")
        while self.running:
            try:
                message = await self.rep_socket.recv_json()
                action = message.get("action")
                symbol = message.get("symbol")

                if action == "subscribe":
                    if symbol:
                        self.subscribed_symbols.add(symbol)
                        print(f"Subscribed to {symbol}")
                        await self.rep_socket.send_json(
                            {"status": "success", "message": f"Subscribed to {symbol}"}
                        )
                    else:
                        await self.rep_socket.send_json(
                            {"status": "error", "message": "Symbol required"}
                        )
                elif action == "unsubscribe":
                    if symbol:
                        self.subscribed_symbols.discard(symbol)
                        print(f"Unsubscribed from {symbol}")
                        await self.rep_socket.send_json(
                            {
                                "status": "success",
                                "message": f"Unsubscribed from {symbol}",
                            }
                        )
                    else:
                        await self.rep_socket.send_json(
                            {"status": "error", "message": "Symbol required"}
                        )
                else:
                    await self.rep_socket.send_json(
                        {"status": "error", "message": "Invalid action"}
                    )
            except Exception as e:
                print(f"Error handling request: {e}")
                # Send error response if possible, otherwise just log
                try:
                    await self.rep_socket.send_json(
                        {"status": "error", "message": str(e)}
                    )
                except Exception:
                    pass

    async def produce_data(self):
        print("Starting data production...")
        while self.running:
            if not self.subscribed_symbols:
                await asyncio.sleep(1)
                continue

            # Only generate data for subscribed symbols
            # For dummy data purposes, we iterate over subscribed symbols
            # In a real scenario, we might be receiving a stream and filtering
            for symbol in list(self.subscribed_symbols):
                price = round(random.uniform(100, 20000), 2)
                tick = {
                    "symbol": symbol,
                    "price": price,
                    "timestamp": asyncio.get_event_loop().time(),
                }
                topic = f"market_data.{symbol}"
                try:
                    await self.pub_socket.send_multipart(
                        [topic.encode(), json.dumps(tick).encode()]
                    )
                except Exception as e:
                    print(f"Error publishing data: {e}")

            await asyncio.sleep(0.1)

    def stop(self):
        self.running = False
        self.pub_socket.close()
        self.rep_socket.close()
        self.context.term()


if __name__ == "__main__":
    service = DataService()
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        service.stop()
