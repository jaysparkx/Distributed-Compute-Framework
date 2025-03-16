import requests
import time
import argparse

HEAD_NODE_URL = "http://localhost:5001"  # Replace with head node public IP or ngrok URL
USER_ID = "user_1"

def submit_task(task_type, num_nodes, priority="low", os_type=None):
    payload = {
        "user_id": USER_ID,
        "type": task_type,
        "num_nodes": num_nodes,
        "priority": priority
    }
    
    # Add OS type preference if specified
    if os_type:
        payload["os_type"] = os_type
        
    response = requests.post(f"{HEAD_NODE_URL}/submit_task", json=payload, timeout=10)
    return response.json()

def check_status(task_id):
    response = requests.get(f"{HEAD_NODE_URL}/task_status/{task_id}", timeout=10)
    return response.json()

def run_task(task_type, num_nodes, priority="high", os_type=None):
    print(f"Submitting {task_type} task with {num_nodes} nodes" + 
          (f" (OS: {os_type})" if os_type else "..."))
          
    task_response = submit_task(task_type, num_nodes, priority, os_type)
    
    if "task_id" not in task_response:
        print(f"Task submission failed: {task_response}")
        return
    
    task_id = task_response["task_id"]
    print(f"Task ID: {task_id}")

    while True:
        status = check_status(task_id)
        print(f"Task status: {status}")
        if status["status"] == "completed":
            print(f"Task completed! Results available.")
            break
        elif status["status"] == "error":
            print(f"Task failed: {status['message']}")
            break
        time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Compute Client")
    parser.add_argument("--task", choices=["matrix_mult", "pytorch_train"], 
                        required=True, help="Type of task to run")
    parser.add_argument("--nodes", type=int, default=2, 
                        help="Number of compute nodes to use")
    parser.add_argument("--priority", choices=["low", "medium", "high"], 
                        default="high", help="Task priority")
    parser.add_argument("--server", type=str, 
                        help="Head node URL (default: http://localhost:5001)")
    parser.add_argument("--os", choices=["mac", "windows"], 
                        help="Preferred OS type for computation")
    
    args = parser.parse_args()
    
    if args.server:
        HEAD_NODE_URL = args.server
        
    run_task(args.task, args.nodes, args.priority, args.os) 