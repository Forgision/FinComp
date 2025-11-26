# Software Requirement Specification (SRS) for Design of Project for Algo Trading Agent

## Project Overview

**Inspired from**: [OpenAlgo](https://github.com/marketcalls/openalgo)
**FinComp (OpenAlgo)** is a comprehensive algorithmic trading platform. It provides a unified interface for interacting with multiple Indian stock brokers, streaming real-time market data, and deploy automated/semi automated trading strategies.

## Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI (Async) + Jinja2 + Alpine.js (for reactivity)
- **Frontend Architecture**: Progressive Web App (PWA)
- **Database**: SQLAlchemy 2.0 (Async), SQLite/MySQL
- **Messaging/IPC**: **ZeroMQ (PyZMQ)** for all inter-process communication and state management (PUB/SUB, REQ/REP).
- **Real-time**: Socket.IO (python-socketio) - Updates every 1 second
- **Task Scheduling**: APScheduler
- **Concurrency**: Multiprocessing (Supervisor + Workers) + Asyncio
- **Testing**: Pytest

## System Architecture

The application is structured into **four main independent processes** to ensure stability, fault isolation, and performance.

### 1. Web Server Process (`app/web`)

- **Host**: FastAPI + Socket.IO.
- **Role**: Handles UI requests, REST API, and WebSocket streaming to frontend.
- **Interaction**:
  - **Requests Snapshot**: Uses ZeroMQ REQ socket to request initial market data state from the Data Engine.
  - **Subscribes to ZeroMQ**: Streams real-time ticks to the frontend via Socket.IO (SUB socket).

### 2. Data Engine Process (`app/core/data`)

- **Host**: Asyncio Event Loop (Single Process).
- **Role**: Dedicated process for ingesting market data.
- **Responsibilities**:
  - Manages WebSocket connections to Brokers (Zerodha, Fyers, etc.).
  - Normalizes incoming ticks.
  - **ZeroMQ Publisher**: Publishes ticks to a ZeroMQ PUB socket (Topic: `market_data`).
  - **ZeroMQ Replier**: Listens on a REP socket to serve "Snapshot" requests (e.g., LTP, Volume) to the Web Server or Algo Engine.
- **Isolation**: If this process lags or crashes, it does not affect active orders or the UI.

### 3. Algo Engine Process (`app/algo`)

- **Host**: Multiprocessing Supervisor.
- **Role**: Manages Strategy execution.
- **Architecture**: **Supervisor + Worker Model**.
  - **Supervisor Process**: Manages the lifecycle of worker processes.
  - **Worker Processes**: A fixed number of long-lived worker processes as per CPU core count (e.g., 3-4 workers).
  - Strategies are distributed and deployed across these worker processes.
- **Responsibilities**:
  - **Subscribes to ZeroMQ**: Listens to `market_data` topic on the SUB socket.
  - Runs strategy logic (CPU bound).
  - Publishes **Signals** to ZeroMQ PUB socket (Topic: `signals`).

### 4. Execution Engine Process (`app/core/execution`)

- **Host**: Asyncio Event Loop.
- **Role**: Order Management System (OMS).
- **Responsibilities**:
  - Subscribes to **Signals** from ZeroMQ (Topic: `signals`).
  - **Order Validation**: Validates signals against broker policies (e.g., quantity, margin).
  - **Execution**: Converts signals to broker-specific order formats and executes via Broker APIs.
  - **Gateway**: Acts as the single gateway for all order execution (Strategies & Web).
  - Manages the master OrderBook and TradeBook.

## Data Sharing & Concurrency

### ZeroMQ (The "Nervous System")

We use **ZeroMQ (ZMQ)** for all inter-process communication, replacing the need for a central cache like Redis.

- **Pattern 1: Pub/Sub (Real-time Data)**
  - **Transport**: TCP (Localhost) or IPC.
  - **Flows**:
    - `Market Data`: Data Engine (PUB) -> Algo Engine (SUB) & Web Server (SUB).
    - `Signals`: Algo Engine (PUB) -> Execution Engine (SUB).
    - `Control`: Web Server (PUB) -> Algo Engine (SUB) (Start/Stop Strategies).

- **Pattern 2: Req/Rep (State/Snapshots)**
  - **Flows**:
    - `Snapshot`: Web Server (REQ) -> Data Engine (REP).
      - *Use Case*: When a user opens the dashboard, the Web Server requests the current "Last Traded Price" for all visible symbols.

### Concurrency Strategy

- **I/O Bound** (Data, Web, Execution): Use **Asyncio**.
- **CPU Bound** (Algo): Use **Multiprocessing** (Supervisor + Long-lived Workers).

## Key Workflows

- **Authentication**: Users log in using **Fyers OAuth** flow (similar to "Login with Google"). No local password management required.
- **Order Management**: Unified order placement API that routes requests to the specific broker adapter.
- **Market Data**: Websocket connection to brokers to receive tick data, which is then broadcasted via ZeroMQ.
- **Telegram Integration**: (Future Scope) Two-way communication via Telegram for alerts.

## Development Guidelines

- **Async/Await**: The codebase heavily relies on Python's `asyncio`. Ensure all I/O bound operations are awaited.
- **Dependency Injection**: Services are typically instantiated and used via dependency injection or factory patterns.
- **Testing**: Run tests using `pytest`. Ensure new features have corresponding unit/integration tests.

## System Requirements (**RECOMMENDED DESIGN PATTERNS**)

- Web interface (Progressive Web App - PWA). It MUST be real-time (1s latency) and have following functionality.
  - Dashboard with following information.
    - Market Summary with following information.
      - NIFY 50, NIFTY 200, NIFTY 500, BANKNIFTY, NIFTY MIDCAP, NIFTY SMALLCAP, etc.
      - **Real-time Data**: Must stream Change, Change%, and OHLC (Open, High, Low, Close).
      - Advancers and Decliners (Simple count display, e.g., "30 Adv / 20 Dec").
      - Top Gainers and Losers with percentage.
      - Top Volume Traded with percentage.
      - Top Value Traded with percentage.
      - Top OI Traded with percentage.
    - Counter of deployed strategies.
      - Counter of open positions amount by strategy.
      - P&L percentage and amount by strategy.
    - Total Today P&L Realized and Unrealized.
    - Total Open Positions (today and previous day) with quantity and average price and profit/loss percentage, profit/loss amount.
    - Total Utilised Margin and Margin Available
    - Recent 5 Orders (Exactly the last 5 orders regardless of status) with info like symbol, quantity, average price, buy/sell, etc, strategy id, timestamp, etc.
  - Orders Page:
    - Showing all order segrageted as per status (open, complete, cancelled, rejected).
    - Showing all position segrageted as per status (open, closed).
    - Showing all trade which is executed order with info like average price, quantity, buy/sell, etc, strategy id, timestamp, etc.
  - Positions Page:
    - Showing all position segrageted as per status (open, closed).
    - Showing all trade which is executed order with info like average price, quantity, buy/sell, etc, strategy id, timestamp, etc.
  - Holdings Page:
    - Showing all holdings with info like symbol, quantity, average price, profit/loss percentage, profit/loss amount accorss all strategies (which are deployed) and brokers (which are active).
  - Strategy Page:
    - Deploy new strategy functionality.
      - User selects from a **predefined, hardcoded list** of strategies.
      - Future Scope: Python file upload capability.
    - Showing all strategy with info like strategy id, strategy name, strategy type, strategy status, strategy p&l percentage, strategy p&l amount, total amount of open positions by strategy, total amount of closed positions by strategy, total amount of trades by strategy, total amount of orders by strategy, strategy timestamp, etc.
    - **Kill Switch**:
      - **Hard Kill**: Cancel ALL pending orders + Close ALL open positions + Undeploy ALL strategies.
      - **Soft Kill**: Cancel ALL pending orders + Undeploy ALL strategies (Positions remain open).
  - Settings Page:
    - Telegram Integration (Future Scope):
      - Two-way communication via Telegram for alerts.
      - Showing all telegram commands with info like command, description, usage, etc.
    - Broker Integration:
      - Showing all broker with info like broker id, broker name, broker type, broker status, last checked timestamp, etc.
      - Broker connection status with info like broker id, broker name, broker type, broker status, last checked timestamp, etc.
      - Showing all settings with info like api key, api secret, api url, etc.
- Backend should have following functionality.
  - Web Server Module (frontend and backend):
    This module have all code related to web server functionality for frontend and backend. This module use fastapi for backend, fastapi with jinja2 for frontend and python `python-socketio` package for web socket server. Such as following functionality;
    - Routes for frontend.
    - API for frontend.
    - API for orders, account, positions, trades, holdings, strategies, settings, etc.
    - **Order Management**:
      - **Manual Trading is DISABLED**. Users cannot place new manual Buy/Sell orders.
      - Allowed Actions: **Cancel** existing orders, **Square Off** (Close) existing positions.
    - WebSocket for real-time data streaming to frontend with async functionality.
      - Set up web socket server using python-socketio on web server start.
      - Connect/Disconnect web socket server with web server lifecycle.
      - **Subscribe to ZeroMQ** to receive real-time ticks and forward to frontend clients.
    - services required for backend functionality.
  - Core Module:
    - This module have all code related to core functionality of the application which is common to all modules. Such as following functionality;
      - Database Management:
        - Database connection using SQLAlchemy 2.0.
        - Database session using AsyncSession.
        - Database models.
        - Database operations.
        - Database transactions.
        - Database queries using SQLAlchemy 2.0.
      - Logging Management:
        - This module will only provide logging functionality to all modules which use for debugging and monitoring. It is not for mobule specific logging such as Strategy Manager Logs.
        - Handling database operations for logs.
      - Data Provider Service (Core Module):
        - Acts as the central facade for all market data requirements.
        - **Responsibilities**:
          - Manage the registry of all active subscriptions (Symbol/Index).
          - Interface with `Broker Manager` to initiate actual data streams.
          - Normalizes incoming data from `Broker Manager` into a standard format.
          - **Broadcasts normalized data via ZeroMQ**.
      - Event Bus (System-Wide Notifications):
        - A central asynchronous event dispatcher.
        - **Events**:
          - `DATA_STREAMING_STARTED`: Payload includes provider ID.
          - `DATA_STREAMING_STOPPED`: Payload includes reason.
          - `MARKET_DATA_UPDATE`: (Optional) For low-frequency broadcasts.
        - **Mechanism**:
          - `DataProvider` publishes `DATA_STREAMING_STARTED`.
          - `AlgoModule` (and others) subscribe to this event on startup.
          - When the event fires, `AlgoModule` triggers its deployment logic.
          - Registry for all subscriptions
            - Registry should be in memory with thread safe and in database.
            - On updating subscription, it should update in memory and in database.
            - Database is only used for backup and persistence.
          - subscribe/unsubscribe symbols for data streaming.

          - Notify all subscribers on receiving new data from data provider.
          - Move to fallback data provider if one data provider is not available.
          - Subscription management for data streaming.
            - Subscription can be individual symbol wise or index wise or all. Subscription can be unique for each symbol, don't register multiple subscriptions for same symbol, if already registered then update the subscription.
            - On receiving new subscription request,
              - Check data provide broker limit.
              - Check if subscription is already registered for same symbol or index of symbol.
              - If limit is reached, then move to next data provider, else subscribe to data streaming.
            - On receiving unsubscribe request,
              - Check if subscription is already registered or not.
              - If symbol is subscribed as part of index, then don't unsubscribe, else unsubscribe from data streaming.
  - Broker Manager Module:
    This module contains the core logic for interacting with brokers. It is designed as a **library** to be instantiated by specific processes (Data Engine, Execution Engine).
    - Authentication and authorization for brokers.
    - **State Management**: Broker connection status is shared across processes using **ZeroMQ PUB/SUB**.
      - `Data Engine` publishes data connection status.
      - `Execution Engine` publishes trade connection status.
      - `Web Server` subscribes to these topics to maintain a real-time registry for the UI.
    - Broker Manager Class:
      - It is registry of all brokers and their connection status.
      - All functionality related to brokers should be managed by Broker Manager.
      - Manage all brokers and their connection status.
      - Data Streaming Adapter:
        - Provides a standardized interface for the Core Data Provider to consume.
        - Handles the specific protocol details of the connected broker (e.g., WebSocket management).
      - Broker Registry & Filtering:
        - `get_active_brokers(capability=None)`: Returns brokers matching the requested capability (e.g., only DATA brokers).
        - `get_fallback_broker(broker_id, capability)`: Intelligent fallback finding another broker with the *same* capability. **Note: Fallback is only supported for DATA capability.**
      - Order Management Functionality:
        - Manage orders across brokers with the ability to:
          - Place order which broker id.
          - Cancel order which broker id single or multiple or all.
          - Modify order which broker id single or multiple or all.
          - Recive signal from Position Size Manager and execute trade.
      - Account Management Functionality:
        - Order Book Management Functionality:
          - Consolidated OrderBook from all brokers which are active.
        - Trade Book Management Functionality:
          - Consolidated TradeBook from all brokers which are active.
        - Position Book Management Functionality:
          - Broker wise position book management which broker id.
        - Holding Book Management Functionality:
          - Consolidated HoldingBook from all brokers which are active.
        - Broker Registry:
          - Register new broker.
            - Each registered broker should have fallback broker id in case of any error.
          - Unregister broker.
          - Get all brokers.
          - Get broker by id.
          - Get broker by name.
          - Get broker by type.
          - Get broker by status.
          - Get broker by last checked timestamp.
        - Data Streaming Provider (Broker) functionality:
          - Get broker for data streaming.
          - Fallback mechanism to get data from other active brokers if one broker is not available.
          - This is only provide active brokers which setup for providing data streaming.

      - Brokers (sub-module):
      This module also have sub-modules named `brokers`, which have all code related to specific brokers. Each broker should have functionality to manage orders, account, positions, trades, holdings, etc of their own. Such as following functionality;
      - Broker Capability Enum:
        - `ORDER`: Can execute trades.
        - `DATA`: Can stream real-time market data.
        - `BOTH`: Supports both.

      - Broker State:
        - `is_active`: Boolean, master switch.
        - `capabilities`: List of `BrokerCapability`.
        - `connection_status`: Connected/Disconnected.
        - `data_streaming_status`: Streaming/Idle (if DATA capability exists).
        - Broker:
          This is base class for all brokers. Broker should have following functionality.
          - Get broker id.
          - Get broker name.
          - Get broker type.
          - Get broker status.
          - Get broker last checked timestamp.
          - Get broker connection status.
          - Order Management Functionality:
            - Place order.
            - Cancel order.
            - Modify order.
          - Get order book.
          - Get trade book.
          - Get position book.
          - Get holding book.
          - authenticate broker.
          - disconnect broker.
          - get real-time data.
  - Algo Module:
    This module have all code/modules/packages related to algo trading functionality. Such as following;
    - Strategy Manager Module (sub-module):
      This module have all code related to managing strategies. Base strategy class, Strategy Manager Class, etc.
      - Strategy Manager Class: It act as a registry of all strategies and their status. It should have following functionality.
        - Register new strategy.
        - Unregister strategy.
        - Get all strategies.
        - Get strategy by id.
        - Get strategy by name.
        - Get strategy by status.
        - Get strategy by type.
        - Deploy/Undeploy strategy (partialar strategy or all strategies).
        - Get strategy stats.
        - Notify all strategies on receiving new data from DataProvider.
      - Logs Management Functionality for strategies:
        - Logs for all trigger points generated by strategies with info such as strategy id, symbol, price, single type or all types.
        - Handling database for logs.
      - Base Strategy Class: It is base class for all strategies. It should have following functionality.
        - Get strategy id.
        - Get strategy name.
        - Get strategy type.
        - Get strategy status.
        - Get strategy last checked timestamp.
        - Deploy/Undeploy strategy.
          - On deploy;
            - it should register itself to Strategy Manager.
            - it should subscribe to data streaming for all required symbols in strategy.
          - On undeploy;
            - it should unregister itself from Strategy Manager.
            - it should unsubscribe from data streaming for all required symbols in strategy.
        - Core logic for strategy execution.
        - Generate signal on matching strategy logic. Generated signal sent to Position Size Manager. Signal should have following information.
          - Strategy id.
          - Symbol.
          - Price.
          - Single type (buy or sell).
          - SL Price (Optional).
          - TP Price (Optional).
        - Logs Management Functionality filtered from strategy manager logs.
        - May have risk management rules specific to strategy, if not then it will use global risk management rules.
    - Risk Management Module (sub-module):
      This module have all code related to managing risk. Base risk class, Risk Manager Class, etc.
      - Risk Manager Class:
        - It calculate risk and reward for each signal generated by strategies.
        - Once risk is calculated, then audit risk and reward as per risk management rules.
        - Once audit is done, then take decision to execute trade or not.
        - If decision is to execute trade, then it **Publishes a Signal** to ZeroMQ (Topic: `signals`).
        - Risk Management Rules can be global, strategy specific.
          - Global Risk Management Rules superceeds all other rules.
      - Position Size Management Module (sub-module):
        This module should have functionality to calculate position size for each signal generated by strategies as per risk manager rules.
        - Position Size Manager Class:
          - This class has main goal to calculate quantity for each signal generated by strategies as per risk management rules.
          - It can override tp and sl price of signal as per risk management rules, but entry price will not be overridden.
          - Once, quantity is calculated, then it send to broker manager to execute trade.

## Data Structures

- **Signal**:
  - `strategy_id`: str
  - `symbol`: str
  - `entry_price`: float
  - `stop_loss`: float
  - `target_price`: float
  - `timestamp`: int
  - `signal_type`: str (BUY/SELL)

- **OrderRequest** (Inherits Signal):
  - `quantity`: int
  - `estimated_pnl`: float
  - `validity`: str (DAY/IOC)
  - `order_type`: str (MARKET/LIMIT)

- **Control Message**:
  - `request_id`: str
  - `command`: str
  - `payload`: dict

## Configuration & Logging

- **Centralized Configuration**:
  - Settings (API Keys, Secrets) are stored in the **Database**.
  - A **Config Service** provides access to these settings.
  - On startup, processes fetch config from the DB.
- **Logging**:
  - Future Scope: Logs will be stored in the database.
  - Currently: File-based logging with rotation.

- Flow of the application:
  - Application start. On start, do followings;
    - Start Broker Manager.
      - Get all active brokers from database.
      - Check and Start all active brokers.
      - Check and Start data streaming for all active brokers.
      - Notify running state to Application.
    - Start Web Server Module.
      - Start FastAPI server.
      - Start WebSocket server.
      - Connect to ZeroMQ (Subscriber) for real-time data.
      - Notify running state to Application.
    - Start Data Provider.
      - Get data provider from Broker Manager.
      - Data Provider required authentication, then wait for authentication to complete (Authentication is done from frontend).
      - Once authentication is complete or not required authentication, then start data streaming for all subscriptions.
      - Notify running state to Broker Manager and Algo Module.
      - On data streaming start/stop/error, notify to Strategy Manager, Algo Module and Web Server Module to start/stop/error data streaming.
      - On data receving new data, notify to Strategy Manager, Algo Module and Web Server Module to process new data.
    - Start Algo Module.
      - Start Strategy Manager (Supervisor).
      - Load all strategies from database.
      - Set initial status of deployed strategies to `WAITING_FOR_DATA`.
      - Subscribe to `DATA_STREAMING_STARTED` event from Data Provider.
      - **On `DATA_STREAMING_STARTED` event**:
        - Verify required data feeds are active.
        - Transition applicable strategies to `RUNNING` (Deploy to Worker Processes).
