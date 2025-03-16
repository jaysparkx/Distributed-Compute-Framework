# User Client Setup

## Prerequisites
- Python 3.9+
- Jupyter Notebook

## Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install jupyter
   ```

2. **Update Configuration**:
   Open `user_client_notebook.ipynb` and set `HEAD_NODE_URL` to the head node's public IP or ngrok URL (e.g., `http://abc123.ngrok.io`).

3. **Run Notebook**:
   ```bash
   jupyter notebook
   ```
   Open `user_client_notebook.ipynb` and run the cells. 