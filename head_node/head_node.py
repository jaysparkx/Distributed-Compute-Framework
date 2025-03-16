import zmq
import pika
import json
import threading
import time
import numpy as np
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger
import logging
from threading import Lock

app = Flask(__name__)

# Logging setup
logger = logging.getLogger()
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(context_id)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

# Global state
connected_nodes = {}  # {node_id: {"capabilities": {}, "last_seen": timestamp, "status": "active", "os_type": "mac|windows"}}
active_tasks = {}    # {task_id: {"status": "", "results": [], "subtasks": {}, "num_nodes": 0}}
state_lock = Lock()

# Initialize RabbitMQ
def init_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_declare(queue='results_queue', durable=True)
    return connection, channel

try:
    rabbitmq_connection, rabbitmq_channel = init_rabbitmq()
    logger.info("RabbitMQ initialized successfully", extra={"context_id": "startup"})
except Exception as e:
    logger.error(f"Failed to initialize RabbitMQ: {e}", extra={"context_id": "startup"})
    rabbitmq_connection, rabbitmq_channel = None, None

# Initialize ZeroMQ
def init_zmq():
    context = zmq.Context()
    registration_socket = context.socket(zmq.REP)
    registration_socket.bind("tcp://*:5555")
    task_socket = context.socket(zmq.PUB)
    task_socket.bind("tcp://*:5556")
    results_socket = context.socket(zmq.PULL)
    results_socket.bind("tcp://*:5557")
    heartbeat_socket = context.socket(zmq.REP)
    heartbeat_socket.bind("tcp://*:5558")
    return registration_socket, task_socket, results_socket, heartbeat_socket

try:
    registration_socket, task_socket, results_socket, heartbeat_socket = init_zmq()
    logger.info("ZeroMQ sockets initialized successfully", extra={"context_id": "startup"})
except Exception as e:
    logger.error(f"Failed to initialize ZeroMQ sockets: {e}", extra={"context_id": "startup"})
    exit(1)

# Handle node registrations
def handle_registrations():
    while True:
        try:
            message = registration_socket.recv_json()
            node_id = message["node_id"]
            
            # Determine OS type from node_id or IP address
            ip_address = message.get("ip_address", "")
            os_type = "unknown"
            if "mac" in node_id.lower() or "mac" in ip_address.lower():
                os_type = "mac"
            elif "windows" in node_id.lower() or "windows" in ip_address.lower():
                os_type = "windows"
            
            with state_lock:
                connected_nodes[node_id] = {
                    "capabilities": message["capabilities"],
                    "last_seen": time.time(),
                    "status": "active",
                    "os_type": os_type
                }
            logger.info(f"Node {node_id} registered with OS type: {os_type}", extra={"context_id": "registration"})
            registration_socket.send_json({"status": "registered"})
        except Exception as e:
            logger.error(f"Registration error: {e}", extra={"context_id": "registration"})
            registration_socket.send_json({"status": "error", "message": str(e)})

# Handle heartbeats
def handle_heartbeats():
    while True:
        try:
            message = heartbeat_socket.recv_json()
            node_id = message["node_id"]
            with state_lock:
                if node_id in connected_nodes:
                    connected_nodes[node_id]["last_seen"] = time.time()
                    connected_nodes[node_id]["status"] = "active"
            heartbeat_socket.send_json({"status": "ack"})
        except Exception as e:
            logger.error(f"Heartbeat error: {e}", extra={"context_id": "heartbeat"})
            heartbeat_socket.send_json({"status": "error"})

# Process results
def process_results():
    while True:
        try:
            result = results_socket.recv_json()
            task_id = result["task_id"]
            subtask_id = result["subtask_id"]
            with state_lock:
                if task_id in active_tasks:
                    active_tasks[task_id]["results"].append(result["result"])
                    active_tasks[task_id]["subtasks"][subtask_id]["status"] = "completed"
                    logger.info(f"Received result for task {task_id}, subtask {subtask_id}", extra={"context_id": "results"})
                    if all(subtask["status"] == "completed" for subtask in active_tasks[task_id]["subtasks"].values()):
                        active_tasks[task_id]["status"] = "completed"
        except Exception as e:
            logger.error(f"Result processing error: {e}", extra={"context_id": "results"})

# Start background threads
threading.Thread(target=handle_registrations, daemon=True).start()
threading.Thread(target=handle_heartbeats, daemon=True).start()
threading.Thread(target=process_results, daemon=True).start()

# Flask API: Submit task
@app.route('/submit_task', methods=['POST'])
def submit_task():
    data = request.json
    task_id = str(int(time.time() * 1000))
    task_type = data["type"]
    num_nodes = data.get("num_nodes", 1)
    user_id = data.get("user_id", "user_1")
    priority = data.get("priority", "low")
    # New parameter to specify OS type preference (optional)
    preferred_os = data.get("os_type", None)  # "mac", "windows", or None for any

    with state_lock:
        # Filter available nodes based on OS preference if specified
        if preferred_os:
            available_nodes = [n for n, info in connected_nodes.items() 
                             if info["status"] == "active" and info["os_type"] == preferred_os]
            if not available_nodes:
                return jsonify({
                    "status": "error", 
                    "message": f"No active {preferred_os} nodes available"
                })
        else:
            # Group nodes by OS type
            mac_nodes = [n for n, info in connected_nodes.items() 
                       if info["status"] == "active" and info["os_type"] == "mac"]
            windows_nodes = [n for n, info in connected_nodes.items() 
                           if info["status"] == "active" and info["os_type"] == "windows"]
            other_nodes = [n for n, info in connected_nodes.items() 
                         if info["status"] == "active" and info["os_type"] not in ["mac", "windows"]]
            
            # Prefer to use nodes of the same OS type to avoid mixing
            if len(mac_nodes) >= num_nodes:
                available_nodes = mac_nodes
                logger.info(f"Using {num_nodes} Mac nodes for task {task_id}", extra={"context_id": "submit_task"})
            elif len(windows_nodes) >= num_nodes:
                available_nodes = windows_nodes
                logger.info(f"Using {num_nodes} Windows nodes for task {task_id}", extra={"context_id": "submit_task"})
            else:
                # Not enough nodes of a single OS type, need to combine (should be avoided)
                available_nodes = mac_nodes + windows_nodes + other_nodes
                logger.warning(f"Mixing node types for task {task_id} - not recommended", 
                              extra={"context_id": "submit_task"})

        if len(available_nodes) < num_nodes:
            return jsonify({
                "status": "error", 
                "message": f"Requested {num_nodes} nodes, only {len(available_nodes)} available"
            })

        selected_nodes = available_nodes[:num_nodes]
        subtasks = {}

        if task_type == "matrix_mult":
            matrix_a = np.random.rand(1000, 1000)
            matrix_b = np.random.rand(1000, 1000)
            chunk_size = 1000 // num_nodes
            for i, node_id in enumerate(selected_nodes):
                start = i * chunk_size
                end = start + chunk_size if i < num_nodes - 1 else 1000
                subtask_id = f"{task_id}_{i}"
                subtasks[subtask_id] = {"status": "pending", "node_id": node_id}
                task_data = {
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "node_id": node_id,
                    "type": task_type,
                    "data": {
                        "matrix_a_chunk": matrix_a[start:end].tolist(),
                        "matrix_b": matrix_b.tolist()
                    }
                }
                task_socket.send_json(task_data)
                if rabbitmq_channel:
                    rabbitmq_channel.basic_publish(exchange='', routing_key='task_queue', body=json.dumps(task_data))

        elif task_type == "pytorch_train":
            inputs = np.random.randn(1000, 784)
            targets = np.random.randint(0, 10, (1000,))
            chunk_size = 1000 // num_nodes
            for i, node_id in enumerate(selected_nodes):
                start = i * chunk_size
                end = start + chunk_size if i < num_nodes - 1 else 1000
                subtask_id = f"{task_id}_{i}"
                subtasks[subtask_id] = {"status": "pending", "node_id": node_id}
                task_data = {
                    "task_id": task_id,
                    "subtask_id": subtask_id,
                    "node_id": node_id,
                    "type": task_type,
                    "data": {
                        "inputs": inputs[start:end].tolist(),
                        "targets": targets[start:end].tolist()
                    }
                }
                task_socket.send_json(task_data)
                if rabbitmq_channel:
                    rabbitmq_channel.basic_publish(exchange='', routing_key='task_queue', body=json.dumps(task_data))

        active_tasks[task_id] = {
            "status": "pending",
            "results": [],
            "subtasks": subtasks,
            "num_nodes": num_nodes,
            "type": task_type,
            "user_id": user_id,
            "os_type": connected_nodes[selected_nodes[0]]["os_type"] if selected_nodes else "unknown"
        }
    
    logger.info(f"Task {task_id} submitted with {num_nodes} nodes", extra={"context_id": "submit_task"})
    return jsonify({"status": "success", "task_id": task_id})

# Flask API: Check task status
@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    with state_lock:
        if task_id not in active_tasks:
            return jsonify({"status": "error", "message": "Task not found"})
        task = active_tasks[task_id]
        if task["status"] == "completed":
            if task["type"] == "matrix_mult":
                result = np.vstack(task["results"])
                return jsonify({"status": "completed", "results": result.tolist()})
            elif task["type"] == "pytorch_train":
                aggregated_grads = {}
                for grad_dict in task["results"]:
                    for name, grad in grad_dict.items():
                        if name not in aggregated_grads:
                            aggregated_grads[name] = np.array(grad)
                        else:
                            aggregated_grads[name] += np.array(grad)
                for name in aggregated_grads:
                    aggregated_grads[name] = (aggregated_grads[name] / len(task["results"])).tolist()
                return jsonify({"status": "completed", "results": aggregated_grads})
        return jsonify({"status": "pending"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 