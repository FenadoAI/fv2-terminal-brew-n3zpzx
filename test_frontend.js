const axios = require('axios');

// Test frontend accessibility
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:3000';

async function testFrontend() {
    console.log('🚀 Testing Coffee Shop Terminal Frontend\n');

    try {
        // Test 1: Check if frontend is accessible
        console.log('1. Testing frontend accessibility...');
        const frontendResponse = await axios.get(FRONTEND_URL, { timeout: 5000 });
        console.log('   ✓ Frontend is accessible');

        // Test 2: Check if API is reachable from frontend context
        console.log('2. Testing API connectivity...');
        const apiResponse = await axios.get(`${API_BASE}/api/`, { timeout: 5000 });
        console.log(`   ✓ API is accessible: ${apiResponse.data.message}`);

        // Test 3: Test menu endpoint
        console.log('3. Testing menu endpoint...');
        const menuResponse = await axios.get(`${API_BASE}/api/menu`, { timeout: 5000 });
        console.log(`   ✓ Menu loaded: ${menuResponse.data.length} items`);

        // Test 4: Test shop info endpoint
        console.log('4. Testing shop info endpoint...');
        const infoResponse = await axios.get(`${API_BASE}/api/info`, { timeout: 5000 });
        console.log(`   ✓ Shop info loaded: ${infoResponse.data.name}`);

        console.log('\n🎉 All frontend connectivity tests passed!');
        console.log('\nYou can now:');
        console.log('1. Open http://localhost:3000 in your browser');
        console.log('2. Try these commands in the terminal:');
        console.log('   - help');
        console.log('   - menu');
        console.log('   - info');
        console.log('   - order ethiopian');
        console.log('   - status');

    } catch (error) {
        console.error('❌ Test failed:', error.message);
        if (error.code === 'ECONNREFUSED') {
            console.error('Make sure both frontend (port 3000) and backend (port 8001) are running');
        }
        process.exit(1);
    }
}

testFrontend();