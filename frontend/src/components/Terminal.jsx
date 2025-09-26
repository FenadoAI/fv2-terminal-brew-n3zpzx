import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API = `${API_BASE}/api`;

const Terminal = () => {
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState('');
  const [currentOrder, setCurrentOrder] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const terminalRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Welcome message (mobile-responsive)
    const isMobile = window.innerWidth < 640;
    const welcomeMessage = isMobile ? `
BLACK COFFEE TERMINAL

Premium black coffee only.
No cream, no sugar, no compromises.

Type 'help' to see available commands or 'menu' to browse our selection.
    ` : `
████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║
   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║
   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝

Welcome to Black Coffee Terminal
Premium black coffee only. No cream, no sugar, no compromises.

Type 'help' to see available commands or 'menu' to browse our selection.
    `;

    addToHistory('system', welcomeMessage);
  }, []);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  const addToHistory = (type, content, data = null) => {
    setHistory(prev => [...prev, { type, content, data, timestamp: Date.now() }]);
  };

  const formatCurrency = (amount) => `$${amount.toFixed(2)}`;

  const parseCommand = (input) => {
    const parts = input.trim().toLowerCase().split(' ');
    return {
      command: parts[0],
      args: parts.slice(1)
    };
  };

  const executeCommand = async (input) => {
    const { command, args } = parseCommand(input);

    addToHistory('user', `$ ${input}`);
    setIsLoading(true);

    try {
      switch (command) {
        case 'help':
          addToHistory('system', `Available commands:

menu          - View our coffee selection
info          - Learn about our shop
order <name>  - Place an order (e.g., order ethiopian)
status        - Check current order status
clear         - Clear the terminal
help          - Show this help message

Examples:
  $ menu
  $ order ethiopian yirgacheffe
  $ info
  $ status`);
          break;

        case 'clear':
          setHistory([]);
          addToHistory('system', 'Terminal cleared. Type "help" for available commands.');
          break;

        case 'menu':
          const menuResponse = await axios.get(`${API}/menu`);
          const menuItems = menuResponse.data;

          let menuDisplay = `
╔════════════════════════════════════════════════════════════════╗
║                         COFFEE MENU                            ║
╚════════════════════════════════════════════════════════════════╝

`;
          menuItems.forEach((item, index) => {
            menuDisplay += `${index + 1}. ${item.name} - ${formatCurrency(item.price)}
   Origin: ${item.origin}
   ${item.description}

`;
          });

          menuDisplay += `To order, type: order <coffee name>
Example: $ order ethiopian yirgacheffe`;

          addToHistory('system', menuDisplay, menuItems);
          break;

        case 'info':
          const infoResponse = await axios.get(`${API}/info`);
          const shopInfo = infoResponse.data;

          addToHistory('system', `
╔════════════════════════════════════════════════════════════════╗
║                      ${shopInfo.name}                     ║
╚════════════════════════════════════════════════════════════════╝

${shopInfo.description}

Location: ${shopInfo.location}
Hours: ${shopInfo.hours}

Philosophy:
${shopInfo.philosophy}
          `);
          break;

        case 'order':
          if (args.length === 0) {
            addToHistory('error', 'Please specify a coffee to order. Example: $ order ethiopian');
            break;
          }

          const coffeeSearch = args.join(' ');
          const menuResponse2 = await axios.get(`${API}/menu`);
          const availableCoffees = menuResponse2.data;

          const matchedCoffee = availableCoffees.find(coffee =>
            coffee.name.toLowerCase().includes(coffeeSearch) ||
            coffee.origin.toLowerCase().includes(coffeeSearch)
          );

          if (!matchedCoffee) {
            addToHistory('error', `Coffee "${coffeeSearch}" not found. Type "menu" to see available options.`);
            break;
          }

          const customerName = `Customer_${Date.now()}`;
          const orderData = {
            customer_name: customerName,
            coffee_id: matchedCoffee.id,
            quantity: 1
          };

          const orderResponse = await axios.post(`${API}/orders`, orderData);
          const order = orderResponse.data;
          setCurrentOrder(order);

          addToHistory('success', `
╔════════════════════════════════════════════════════════════════╗
║                       ORDER CONFIRMED                          ║
╚════════════════════════════════════════════════════════════════╝

Order ID: ${order.id}
Coffee: ${order.coffee_name}
Price: ${formatCurrency(order.total_price)}
Status: ${order.status.toUpperCase()}

Your order has been placed! We'll have it ready for pickup shortly.
Type "status" to check your order status.
          `);
          break;

        case 'status':
          if (!currentOrder) {
            addToHistory('system', 'No current order found. Place an order first!');
            break;
          }

          const statusResponse = await axios.get(`${API}/orders/${currentOrder.id}`);
          const orderStatus = statusResponse.data;

          addToHistory('system', `
Order ID: ${orderStatus.id}
Coffee: ${orderStatus.coffee_name}
Status: ${orderStatus.status.toUpperCase()}
Total: ${formatCurrency(orderStatus.total_price)}
Ordered: ${new Date(orderStatus.timestamp).toLocaleString()}
          `);
          break;

        default:
          addToHistory('error', `Command "${command}" not recognized. Type "help" for available commands.`);
          break;
      }
    } catch (error) {
      console.error('Command execution error:', error);
      addToHistory('error', `Error executing command: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const command = input.trim();
    setInput('');
    executeCommand(command);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      // Basic tab completion for common commands
      const commands = ['help', 'menu', 'info', 'order', 'status', 'clear'];
      const matching = commands.filter(cmd => cmd.startsWith(input.toLowerCase()));
      if (matching.length === 1) {
        setInput(matching[0]);
      }
    }
  };

  return (
    <div className="min-h-screen bg-black text-green-400 font-mono p-2 sm:p-4">
      <div className="max-w-6xl mx-auto">
        <div
          ref={terminalRef}
          className="min-h-[calc(100vh-6rem)] sm:min-h-[calc(100vh-8rem)] mb-2 sm:mb-4 overflow-y-auto scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-green-600"
          style={{ maxHeight: 'calc(100vh - 6rem)' }}
        >
          {history.map((entry, index) => (
            <div key={index} className="mb-2">
              {entry.type === 'user' && (
                <div className="text-green-300">{entry.content}</div>
              )}
              {entry.type === 'system' && (
                <div className="text-green-400 whitespace-pre-line">{entry.content}</div>
              )}
              {entry.type === 'success' && (
                <div className="text-green-300 whitespace-pre-line">{entry.content}</div>
              )}
              {entry.type === 'error' && (
                <div className="text-red-400 whitespace-pre-line">{entry.content}</div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="text-yellow-400 animate-pulse">Processing command...</div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex items-center">
          <span className="text-green-300 mr-1 sm:mr-2">$</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent border-none outline-none text-green-400 font-mono text-sm sm:text-lg"
            placeholder="Type a command..."
            disabled={isLoading}
          />
          <div className="text-green-600 ml-1 sm:ml-2 animate-blink">█</div>
        </form>
      </div>
    </div>
  );
};

export default Terminal;