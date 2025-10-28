# 🧠 Helm Installation Guideline — DEDA: Drug Evaluation & Discovery Agent

This guide explains how to install and run DEDA as a Kubernetes Pod using Helm.
Feel free to change the Helm template as necessary.

---

## 🧩 1. Prerequisites
Make sure you have the following installed:
- **Docker**
- **Helm**
- **KIND** — for local Kubernetes testing

---

## 🧱 2. Run DEDA locally (recommended)

Inside `entrypoint.sh` set your `OPENAI_API_KEY`. 

Navigate to the Helm directory inside the project:
```bash
cd deda-drug-evaluation-and-discovery-agent/helm
```

Build docker image:
```bash
docker build --no-cache -t deda ..
```

Then verify that the Docker images is built successfully:
```bash
docker images

```
> ⚠️ **Important:**  
> We **do not recommend embedding your OpenAI API key inside the Docker image**.  
> Always run the container locally where you can safely manage environment variables.  
> If you maintain a **private Docker registry**, you can build and push your own image using:
> ```bash
> docker build -t <your-registry>/deda:latest .
> docker push <your-registry>/deda:latest
> ```
> And then update the `values.yaml` accordingly.


---

## 🧰 3. Running DEDA with KIND (for testing)
If you’d like to see how DEDA runs inside a Kubernetes cluster managed by **KIND**, follow these steps:

### Step 1 — Install KIND
Follow installation instructions from: [https://kind.sigs.k8s.io](https://kind.sigs.k8s.io)

### Step 2 — Create a cluster
```bash
kind create cluster
```

### Step 3 — Load the local Docker image into KIND
```bash
kind load docker-image deda:latest
```

### Step 4 — Deploy using Helm
Once the image is loaded, install the Helm chart:
```bash
helm install deda ./deda
```

You can verify the deployment:
```bash
kubectl get pods
```
