# IX LAB Distributed Compute Framework


A lightweight, scalable distributed computing framework designed for low to mid-sized compute clusters. Built by [IX LAB](https://ixlab.ai) as an open source initiative to democratize distributed computing capabilities.

## Overview

The IX LAB Distributed Compute Framework provides a flexible architecture for distributing computational tasks across heterogeneous nodes (Windows and macOS), with a focus on efficiency, reliability, and ease of deployment. The system enables dynamic resource allocation, fault tolerance through heartbeat monitoring, and cross-platform computation support.

**Visit our websites:**
- [IX LAB](https://ixlab.ai) - Pioneering AI research and development
- [EDITH](https://edithx.ai) - Our AI-driven platform

## Technical Architecture

### System Components

The framework consists of four main components operating in a coordinated architecture:

1. **Head Node**: Central coordinator responsible for task management, node registration, work distribution, and result aggregation.
2. **Provider Nodes (macOS)**: Compute nodes optimized for macOS environments, with MPS acceleration support.
3. **Provider Nodes (Windows)**: Compute nodes optimized for Windows environments, with CUDA acceleration support.
4. **User Client**: Interface for submitting tasks and retrieving results from the distributed system.

### Communication Protocols

The system employs a dual communication strategy:

1. **ZeroMQ (ØMQ)**:
   - **Registration Socket** (REQ-REP): For provider node registration
   - **Task Distribution Socket** (PUB-SUB): For broadcasting tasks to available nodes
   - **Results Socket** (PUSH-PULL): For collecting computation results
   - **Heartbeat Socket** (REQ-REP): For monitoring node health and availability

2. **RabbitMQ** (Complementary queue system):
   - Provides persistent message queuing for enhanced reliability
   - Enables message retention in case of node disconnection
   - Offers a management interface for monitoring system activity

### Technical Capabilities

#### Task Distribution Methodology

The head node employs intelligent task partitioning based on:
- Available compute resources
- Node hardware capabilities
- Operating system compatibility
- Task complexity and divisibility

Tasks are split into subtasks with optimal granularity to maximize parallel execution efficiency while minimizing communication overhead.

#### Supported Computational Patterns

1. **Matrix Multiplication**:
   - Horizontally partitions matrices across available nodes
   - Each node processes a segment of the computation
   - Results are aggregated to form the complete solution

2. **PyTorch Neural Network Training**:
   - Distributes training data across nodes
   - Each node computes gradients on its data partition
   - Results can be aggregated for model parameter updates

#### System Monitoring and Reliability

- **Heartbeat System**: Continuous monitoring of node availability with 5-second intervals
- **State Synchronization**: Thread-safe state management using mutex locks
- **JSON-based Structured Logging**: Comprehensive logging for debugging and performance analysis
- **Graceful Failure Handling**: System resilience during node disconnection or task failures

## Capacity and Limitations

This framework is designed for **low to mid-sized clusters** (typically 2-50 nodes) and prioritizes:

- **Simplicity**: Easy to deploy and understand
- **Flexibility**: Supports heterogeneous hardware and operating systems
- **Low Overhead**: Minimal resource consumption for coordination

**Important Technical Considerations:**

1. **ZeroMQ Scalability**: As an intentional design choice, we use ZeroMQ which provides excellent performance for small to medium-sized clusters. For large-scale deployments (hundreds to thousands of nodes), frameworks like Ray or Apache Spark would be more appropriate.

2. **Network Topology**: The current PUB-SUB model works best in low-latency environments. Wide-area distribution across geographical regions would require architecture modifications.

3. **Task Complexity**: Optimized for compute-intensive tasks where computation time significantly exceeds communication overhead.

4. **Data Transfer**: Large datasets should be partitioned appropriately to avoid network bottlenecks.

## Deployment

### Prerequisites

- Docker and Docker Compose
- For provider nodes: CUDA/MPS-compatible hardware (optional but recommended)
- Network connectivity between all nodes

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ixlab/distributed-compute-framework.git
cd distributed-compute-framework

# Start the system (head node, providers, and RabbitMQ)
docker-compose up -d

# Submit a sample task using the client
cd user_client
python user_client.py --task matrix_mult --nodes 2
```

### Configuration Options

The system can be configured through various parameters:

- **Head Node**:
  - Scale worker processes via environment variables
  - Adjust queue sizes and timeouts for optimal performance
  - Configure logging verbosity

- **Provider Nodes**:
  - Customize resource allocation limits
  - Define specialized capability reporting
  - Enable/disable specific task type support

## Custom Task Implementation

The framework is designed to be extensible. To implement a custom task type:

1. Add the task type handler in the head node's task distribution logic
2. Implement the corresponding computation logic in provider client code
3. Update the user client to support the new task type submission

Example implementation of a custom image processing task:

```python
# In head_node.py
elif task_type == "image_processing":
    image_data = data["image"]
    chunks = split_image_into_chunks(image_data, num_nodes)
    for i, node_id in enumerate(selected_nodes):
        subtask_id = f"{task_id}_{i}"
        subtasks[subtask_id] = {"status": "pending", "node_id": node_id}
        task_data = {
            "task_id": task_id,
            "subtask_id": subtask_id,
            "node_id": node_id,
            "type": task_type,
            "data": {
                "image_chunk": chunks[i]
            }
        }
        task_socket.send_json(task_data)

# In provider_client.py
elif task_type == "image_processing":
    image_chunk = task_data["data"]["image_chunk"]
    processed_chunk = apply_image_filter(image_chunk)
    results_socket.send_json({
        "task_id": task_id,
        "subtask_id": subtask_id,
        "node_id": NODE_ID,
        "status": "completed",
        "result": processed_chunk,
        "timestamp": time.time()
    })
```

## Performance Optimization

For optimal performance:

1. **Task Granularity**: Adjust the number of subtasks based on the computational complexity and available nodes
2. **Hardware Matching**: Assign computation to nodes with appropriate capabilities
3. **Network Configuration**: Ensure low-latency connectivity between nodes
4. **Load Balancing**: Distribute work proportionally to node capabilities

## Future Development

Planned enhancements:

1. **Advanced Scheduling**: Priority-based workload management
2. **Resource Monitoring**: Dynamic resource usage tracking
3. **Checkpointing**: Task state persistence for failure recovery
4. **Security Enhancements**: Authentication and authorization layers
5. **WebUI Dashboard**: Visual monitoring and administration interface

## Technical Benchmarks

Performance testing on various configurations shows:

| Task Type | Cluster Size | Speedup Factor |
|-----------|--------------|---------------|
| Matrix Multiplication (1000x1000) | 2 nodes | 1.8x |
| Matrix Multiplication (1000x1000) | 4 nodes | 3.4x |
| PyTorch Training (MNIST) | 2 nodes | 1.7x |
| PyTorch Training (MNIST) | 4 nodes | 3.1x |

*Note: Actual performance depends on network conditions, node capabilities, and workload characteristics.*

## Contributing

We welcome contributions to enhance the functionality and performance of this framework:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow our coding standards and add appropriate tests for new features.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2023 IX LAB

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Citation

If you use this framework in your research or project, please cite:

```
@software{ixlab_distributed_compute,
  author = {IX LAB},
  title = {IX LAB Distributed Compute Framework},
  url = {https://github.com/ixlab/distributed-compute-framework},
  year = {2023},
}
```

## Contact

For questions, feedback, or collaboration opportunities:

- **Website**: [https://ixlab.ai](https://ixlab.ai)
- **Email**: info@ixlab.ai
- **GitHub Issues**: For bug reports and feature requests 