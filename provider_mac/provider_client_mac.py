import zmq
import pika
import json
import threading
import time
import uuid
import numpy as np
import torch
import torch.nn as nn
from torch.optim import SGD
import psutil
import logging
from pythonjsonlogger import jsonlogger

# Logging setup
logger = logging.getLogger()
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(context_id)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

NODE_ID = str(uuid.uuid4())
HEAD_NODE_ADDRESS = "head-node"  # Docker Compose service name

# ZeroMQ setup
context = zmq.Context()
registration_socket = context.socket(zmq.REQ)
registration_socket.connect(f"tcp://{HEAD_NODE_ADDRESS}:5555")
task_socket = context.socket(zmq.SUB)
task_socket.connect(f"tcp://{HEAD_NODE_ADDRESS}:5556")
task_socket.setsockopt_string(zmq.SUBSCRIBE, "")
results_socket = context.socket(zmq.PUSH)
results_socket.connect(f"tcp://{HEAD_NODE_ADDRESS}:5557")
heartbeat_socket = context.socket(zmq.REQ)
heartbeat_socket.connect(f"tcp://{HEAD_NODE_ADDRESS}:5558")

# Get system capabilities
def get_system_capabilities():
    gpu_type = "mps" if torch.backends.mps.is_available() else "cpu"
    return {
        "cpu_count": psutil.cpu_count(),
        "memory": psutil.virtual_memory().total / (1024 ** 3),
        "gpu": gpu_type
    }

# Register with head node
def register_with_head_node():
    registration_data = {
        "node_id": NODE_ID,
        "capabilities": get_system_capabilities(),
        "ip_address": "mac_provider"
    }
    registration_socket.send_json(registration_data)
    if registration_socket.poll(10000) == 0:
        logger.error("Registration timeout", extra={"context_id": "registration"})
        return False
    response = registration_socket.recv_json()
    if response.get("status") == "registered":
        logger.info("Registered with head node", extra={"context_id": "registration"})
        return True
    logger.error(f"Registration failed: {response.get('message')}", extra={"context_id": "registration"})
    return False

# Send heartbeat
def send_heartbeat():
    while True:
        try:
            heartbeat_socket.send_json({"node_id": NODE_ID, "timestamp": time.time()})
            if heartbeat_socket.poll(5000) == 0:
                logger.warning("Heartbeat timeout", extra={"context_id": "heartbeat"})
            else:
                heartbeat_socket.recv_json()
            time.sleep(5)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}", extra={"context_id": "heartbeat"})
            time.sleep(5)

# Process tasks
def process_task(task_data):
    task_id = task_data["task_id"]
    subtask_id = task_data["subtask_id"]
    task_type = task_data["type"]
    node_id = task_data["node_id"]

    if node_id != NODE_ID:
        return

    logger.info(f"Processing task {task_id}, subtask {subtask_id}", extra={"context_id": "task_processing"})

    # Determine device (MPS or CPU)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    if task_type == "matrix_mult":
        matrix_a_chunk = np.array(task_data["data"]["matrix_a_chunk"])
        matrix_b = np.array(task_data["data"]["matrix_b"])
        result = np.matmul(matrix_a_chunk, matrix_b)
        results_socket.send_json({
            "task_id": task_id,
            "subtask_id": subtask_id,
            "node_id": NODE_ID,
            "status": "completed",
            "result": result.tolist(),
            "timestamp": time.time()
        })
    elif task_type == "pytorch_train":
        try:
            model = nn.Sequential(nn.Linear(784, 128), nn.ReLU(), nn.Linear(128, 10)).to(device)
            inputs = torch.tensor(task_data["data"]["inputs"]).to(device)
            targets = torch.tensor(task_data["data"]["targets"]).long().to(device)
            criterion = nn.CrossEntropyLoss()
            optimizer = SGD(model.parameters(), lr=0.01)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            
            # Modified to avoid using numpy conversion due to compatibility issues
            gradients = {}
            for name, param in model.named_parameters():
                if param.grad is not None:
                    # Convert to CPU tensor and then to list directly
                    gradients[name] = param.grad.cpu().tolist()
            
            results_socket.send_json({
                "task_id": task_id,
                "subtask_id": subtask_id,
                "node_id": NODE_ID,
                "status": "completed",
                "result": gradients,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.error(f"Error processing PyTorch task: {e}", extra={"context_id": "task_processing"})
            results_socket.send_json({
                "task_id": task_id,
                "subtask_id": subtask_id,
                "node_id": NODE_ID,
                "status": "error",
                "error_message": str(e),
                "timestamp": time.time()
            })

# Main loop
def main():
    if not register_with_head_node():
        exit(1)
    
    threading.Thread(target=send_heartbeat, daemon=True).start()
    
    while True:
        try:
            task_data = task_socket.recv_json()
            threading.Thread(target=process_task, args=(task_data,), daemon=True).start()
        except Exception as e:
            logger.error(f"Task reception error: {e}", extra={"context_id": "task_reception"})
            time.sleep(1)

if __name__ == "__main__":
    main() 