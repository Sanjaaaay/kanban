import requests
import sys
from datetime import datetime, timedelta
import json

class KanbanAPITester:
    def __init__(self, base_url="https://taskflow-board-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.board_id = None
        self.task_ids = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_create_board(self):
        """Test board creation"""
        board_data = {
            "name": "Test Kanban Board",
            "description": "Test board for API testing"
        }
        success, response = self.run_test(
            "Create Board",
            "POST",
            "boards",
            200,
            data=board_data
        )
        if success and 'id' in response:
            self.board_id = response['id']
            print(f"   Created board with ID: {self.board_id}")
            return True
        return False

    def test_get_boards(self):
        """Test getting all boards"""
        success, response = self.run_test(
            "Get All Boards",
            "GET",
            "boards",
            200
        )
        if success:
            print(f"   Found {len(response)} boards")
        return success

    def test_get_board_by_id(self):
        """Test getting specific board"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Board by ID",
            "GET",
            f"boards/{self.board_id}",
            200
        )
        return success

    def test_create_task_todo(self):
        """Test creating a task in To Do column"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        task_data = {
            "title": "Test Task - To Do",
            "description": "This is a test task in To Do column",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        success, response = self.run_test(
            "Create Task (To Do)",
            "POST",
            f"boards/{self.board_id}/tasks",
            200,
            data=task_data
        )
        if success and 'id' in response:
            self.task_ids.append(response['id'])
            print(f"   Created task with ID: {response['id']}")
        return success

    def test_create_task_overdue(self):
        """Test creating an overdue task"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        task_data = {
            "title": "Overdue Task",
            "description": "This task is overdue",
            "priority": "medium",
            "due_date": (datetime.now() - timedelta(days=2)).isoformat()
        }
        success, response = self.run_test(
            "Create Overdue Task",
            "POST",
            f"boards/{self.board_id}/tasks",
            200,
            data=task_data
        )
        if success and 'id' in response:
            self.task_ids.append(response['id'])
        return success

    def test_create_task_low_priority(self):
        """Test creating a low priority task"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        task_data = {
            "title": "Low Priority Task",
            "description": "This is a low priority task",
            "priority": "low"
        }
        success, response = self.run_test(
            "Create Low Priority Task",
            "POST",
            f"boards/{self.board_id}/tasks",
            200,
            data=task_data
        )
        if success and 'id' in response:
            self.task_ids.append(response['id'])
        return success

    def test_get_board_tasks(self):
        """Test getting all tasks for a board"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        success, response = self.run_test(
            "Get Board Tasks",
            "GET",
            f"boards/{self.board_id}/tasks",
            200
        )
        if success:
            print(f"   Found {len(response)} tasks")
        return success

    def test_filter_tasks_by_priority(self):
        """Test filtering tasks by priority"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        success, response = self.run_test(
            "Filter Tasks by Priority (High)",
            "GET",
            f"boards/{self.board_id}/tasks",
            200,
            params={"priority": "high"}
        )
        if success:
            print(f"   Found {len(response)} high priority tasks")
        return success

    def test_filter_tasks_by_column(self):
        """Test filtering tasks by column"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        success, response = self.run_test(
            "Filter Tasks by Column (To Do)",
            "GET",
            f"boards/{self.board_id}/tasks",
            200,
            params={"column": "todo"}
        )
        if success:
            print(f"   Found {len(response)} tasks in To Do column")
        return success

    def test_get_task_by_id(self):
        """Test getting specific task"""
        if not self.task_ids:
            print("❌ No task IDs available for testing")
            return False
            
        success, response = self.run_test(
            "Get Task by ID",
            "GET",
            f"tasks/{self.task_ids[0]}",
            200
        )
        return success

    def test_update_task(self):
        """Test updating a task"""
        if not self.task_ids:
            print("❌ No task IDs available for testing")
            return False
            
        update_data = {
            "title": "Updated Test Task",
            "description": "This task has been updated",
            "priority": "medium"
        }
        success, response = self.run_test(
            "Update Task",
            "PUT",
            f"tasks/{self.task_ids[0]}",
            200,
            data=update_data
        )
        return success

    def test_move_task(self):
        """Test moving a task between columns (drag-and-drop)"""
        if not self.task_ids:
            print("❌ No task IDs available for testing")
            return False
            
        move_data = {"column": "in_progress"}
        success, response = self.run_test(
            "Move Task to In Progress",
            "PATCH",
            f"tasks/{self.task_ids[0]}/move",
            200,
            data=move_data
        )
        
        if success:
            # Move to Done column
            move_data = {"column": "done"}
            success2, response2 = self.run_test(
                "Move Task to Done",
                "PATCH",
                f"tasks/{self.task_ids[0]}/move",
                200,
                data=move_data
            )
            return success2
        return success

    def test_delete_task(self):
        """Test deleting a task"""
        if not self.task_ids:
            print("❌ No task IDs available for testing")
            return False
            
        # Delete the last task to keep others for further testing
        task_to_delete = self.task_ids[-1]
        success, response = self.run_test(
            "Delete Task",
            "DELETE",
            f"tasks/{task_to_delete}",
            200
        )
        if success:
            self.task_ids.remove(task_to_delete)
        return success

    def test_delete_board(self):
        """Test deleting a board (cleanup)"""
        if not self.board_id:
            print("❌ No board ID available for testing")
            return False
            
        success, response = self.run_test(
            "Delete Board (Cleanup)",
            "DELETE",
            f"boards/{self.board_id}",
            200
        )
        return success

def main():
    print("🚀 Starting Kanban Board API Tests")
    print("=" * 50)
    
    tester = KanbanAPITester()
    
    # Run all tests in sequence
    test_methods = [
        tester.test_health_check,
        tester.test_root_endpoint,
        tester.test_create_board,
        tester.test_get_boards,
        tester.test_get_board_by_id,
        tester.test_create_task_todo,
        tester.test_create_task_overdue,
        tester.test_create_task_low_priority,
        tester.test_get_board_tasks,
        tester.test_filter_tasks_by_priority,
        tester.test_filter_tasks_by_column,
        tester.test_get_task_by_id,
        tester.test_update_task,
        tester.test_move_task,
        tester.test_delete_task,
        tester.test_delete_board
    ]
    
    for test_method in test_methods:
        try:
            test_method()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All API tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())