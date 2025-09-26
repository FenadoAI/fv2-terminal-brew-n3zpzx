import requests
import time

# Test configuration
BASE_URL = "http://localhost:8001/api"  # Adjusted for backend port

class TestCoffeeShop:
    """Test the complete coffee shop ordering flow"""

    def __init__(self):
        """Setup for tests"""
        self.base_url = BASE_URL
        print(f"Testing against: {self.base_url}")

    def test_get_shop_info(self):
        """Test getting shop information"""
        response = requests.get(f"{self.base_url}/info")
        assert response.status_code == 200

        info = response.json()
        assert info["name"] == "Black Coffee Terminal"
        assert "commands" in info
        assert len(info["commands"]) > 0
        print("✓ Shop info endpoint working")

    def test_get_menu(self):
        """Test getting the coffee menu"""
        response = requests.get(f"{self.base_url}/menu")
        assert response.status_code == 200

        menu = response.json()
        assert isinstance(menu, list)
        assert len(menu) > 0

        # Check first coffee item structure
        coffee = menu[0]
        required_fields = ["id", "name", "origin", "description", "price", "available"]
        for field in required_fields:
            assert field in coffee

        assert coffee["available"] == True
        assert coffee["price"] > 0
        print(f"✓ Menu endpoint working - {len(menu)} items available")
        return menu

    def test_place_order_success(self):
        """Test successfully placing an order"""
        # First get menu
        menu_response = requests.get(f"{self.base_url}/menu")
        assert menu_response.status_code == 200
        menu = menu_response.json()
        assert len(menu) > 0

        # Place order for first coffee
        coffee = menu[0]
        order_data = {
            "customer_name": f"TestCustomer_{int(time.time())}",
            "coffee_id": coffee["id"],
            "quantity": 2
        }

        response = requests.post(f"{self.base_url}/orders", json=order_data)
        assert response.status_code == 200

        order = response.json()
        assert order["coffee_id"] == coffee["id"]
        assert order["coffee_name"] == coffee["name"]
        assert order["quantity"] == 2
        assert order["total_price"] == coffee["price"] * 2
        assert order["status"] == "pending"
        assert "id" in order

        print(f"✓ Order placed successfully - {order['coffee_name']} x{order['quantity']} = ${order['total_price']}")
        return order

    def test_get_order_status(self):
        """Test getting order status"""
        # First place an order
        order = self.test_place_order_success()
        order_id = order["id"]

        # Get order status
        response = requests.get(f"{self.base_url}/orders/{order_id}")
        assert response.status_code == 200

        retrieved_order = response.json()
        assert retrieved_order["id"] == order_id
        assert retrieved_order["status"] == "pending"

        print(f"✓ Order status retrieved - Order {order_id[:8]}... is {retrieved_order['status']}")

    def test_place_order_invalid_coffee(self):
        """Test placing order with invalid coffee ID"""
        order_data = {
            "customer_name": "TestCustomer",
            "coffee_id": "invalid-coffee-id",
            "quantity": 1
        }

        response = requests.post(f"{self.base_url}/orders", json=order_data)
        assert response.status_code == 404

        error = response.json()
        assert "detail" in error
        print("✓ Invalid coffee ID properly rejected")

    def test_get_nonexistent_order(self):
        """Test getting non-existent order"""
        response = requests.get(f"{self.base_url}/orders/nonexistent-id")
        assert response.status_code == 404

        error = response.json()
        assert "detail" in error
        print("✓ Non-existent order properly rejected")

    def test_complete_ordering_workflow(self):
        """Test the complete ordering workflow"""
        print("\n🧪 Testing complete ordering workflow...")

        # Step 1: Get shop info
        info_response = requests.get(f"{self.base_url}/info")
        assert info_response.status_code == 200
        print("  1. ✓ Retrieved shop information")

        # Step 2: Browse menu
        menu_response = requests.get(f"{self.base_url}/menu")
        assert menu_response.status_code == 200
        menu = menu_response.json()
        print(f"  2. ✓ Browsed menu - {len(menu)} coffees available")

        # Step 3: Select and order coffee
        selected_coffee = menu[1] if len(menu) > 1 else menu[0]  # Pick second coffee or first if only one
        order_data = {
            "customer_name": f"WorkflowTest_{int(time.time())}",
            "coffee_id": selected_coffee["id"],
            "quantity": 1
        }

        order_response = requests.post(f"{self.base_url}/orders", json=order_data)
        assert order_response.status_code == 200
        order = order_response.json()
        print(f"  3. ✓ Placed order for {order['coffee_name']}")

        # Step 4: Check order status
        status_response = requests.get(f"{self.base_url}/orders/{order['id']}")
        assert status_response.status_code == 200
        status = status_response.json()
        print(f"  4. ✓ Checked order status - {status['status']}")

        print("🎉 Complete ordering workflow successful!")

if __name__ == "__main__":
    # Run tests directly
    test = TestCoffeeShop()

    try:
        print("🚀 Starting Coffee Shop API Tests\n")

        test.test_get_shop_info()
        test.test_get_menu()
        test.test_place_order_success()
        test.test_get_order_status()
        test.test_place_order_invalid_coffee()
        test.test_get_nonexistent_order()
        test.test_complete_ordering_workflow()

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)