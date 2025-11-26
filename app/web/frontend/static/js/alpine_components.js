document.addEventListener('alpine:init', () => {
    
    // Market Summary Component
    // WebSocket Store
    Alpine.store('websocket', {
        socket: null,
        connected: false,
        indices: [
            { symbol: 'NIFTY 50', ltp: 24350.50, change: 120.50, percent_change: 0.50, color: 'text-success' },
            { symbol: 'BANKNIFTY', ltp: 52100.25, change: -150.75, percent_change: -0.29, color: 'text-danger' }
        ],
        
        connect() {
            this.socket = new WebSocket('ws://' + window.location.hostname + ':8765');
            
            this.socket.onopen = () => {
                console.log('WebSocket Connected');
                this.connected = true;
                this.authenticate();
            };
            
            this.socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };
            
            this.socket.onclose = () => {
                console.log('WebSocket Disconnected');
                this.connected = false;
                // Reconnect after 5 seconds
                setTimeout(() => this.connect(), 5000);
            };
        },
        
        authenticate() {
            this.socket.send(JSON.stringify({
                action: 'auth',
                api_key: 'dev_secret_key'
            }));
        },
        
        subscribe() {
            this.socket.send(JSON.stringify({
                action: 'subscribe',
                symbols: [
                    { symbol: 'NIFTY 50', exchange: 'NSE' },
                    { symbol: 'BANKNIFTY', exchange: 'NSE' }
                ],
                mode: 'LTP'
            }));
        },
        
        handleMessage(message) {
            if (message.type === 'auth' && message.status === 'success') {
                console.log('Authenticated');
                this.subscribe();
            } else if (message.type === 'market_data' || (message.symbol && message.ltp)) {
                 // Handle wrapped data from ZMQ listener
                 const data = message.data || message;
                 const symbol = message.symbol || data.symbol;
                 
                 const index = this.indices.findIndex(i => i.symbol === symbol);
                 if (index !== -1 && data.ltp) {
                     this.indices[index].ltp = data.ltp;
                     this.indices[index].change = data.change;
                     this.indices[index].percent_change = data.percent_change;
                     this.indices[index].color = data.change >= 0 ? 'text-success' : 'text-danger';
                 }
            }
        }
    });

    // Market Summary Component
    Alpine.data('marketSummary', () => ({
        // Use getter to bind to store
        get indices() { return Alpine.store('websocket').indices },
        advancers: 1250,
        decliners: 850,
        topGainers: [],
        topLosers: [],
        loading: false,

        init() {
            // Initialize WebSocket connection
            Alpine.store('websocket').connect();
            
            // Still fetch other static dummy data
            this.fetchData();
        },

        async fetchData() {
            try {
                const response = await fetch('/api/dummy/market-summary');
                const data = await response.json();
                // We only update non-realtime parts here
                this.advancers = data.advancers;
                this.decliners = data.decliners;
                this.topGainers = data.top_gainers;
                this.topLosers = data.top_losers;
            } catch (error) {
                console.error('Error fetching market summary:', error);
            }
        }
    }));

    // Orders Component
    Alpine.data('orders', () => ({
        orders: [],
        loading: true,

        async init() {
            await this.fetchData();
        },

        async fetchData() {
            try {
                const response = await fetch('/api/dummy/orders');
                this.orders = await response.json();
                this.loading = false;
            } catch (error) {
                console.error('Error fetching orders:', error);
            }
        }
    }));

    // Positions Component
    Alpine.data('positions', () => ({
        positions: [],
        loading: true,

        async init() {
            await this.fetchData();
        },

        async fetchData() {
            try {
                const response = await fetch('/api/dummy/positions');
                this.positions = await response.json();
                this.loading = false;
            } catch (error) {
                console.error('Error fetching positions:', error);
            }
        }
    }));

    // Holdings Component
    Alpine.data('holdings', () => ({
        holdings: [],
        loading: true,

        async init() {
            await this.fetchData();
        },

        async fetchData() {
            try {
                const response = await fetch('/api/dummy/holdings');
                this.holdings = await response.json();
                this.loading = false;
            } catch (error) {
                console.error('Error fetching holdings:', error);
            }
        }
    }));

    // Strategies Component
    Alpine.data('strategies', () => ({
        strategies: [],
        loading: true,

        async init() {
            await this.fetchData();
        },

        async fetchData() {
            try {
                const response = await fetch('/api/dummy/strategies');
                this.strategies = await response.json();
                this.loading = false;
            } catch (error) {
                console.error('Error fetching strategies:', error);
            }
        }
    }));
});
