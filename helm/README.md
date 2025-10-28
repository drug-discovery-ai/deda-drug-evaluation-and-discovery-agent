# 🧠 Helm Installation Guideline — DEDA: Drug Evaluation & Discovery Agent

This guide explains how to install and run **DEDA** using Helm, both locally and in a KIND (Kubernetes-in-Docker) cluster.

---

## 🧩 1. Prerequisites
Make sure you have the following installed:
- **Docker**
- **Helm**
- **KIND** — for local Kubernetes testing

---

## 🧱 2. Run DEDA locally (recommended)

Inside `entrypoint.sh` set your OPENAI_API_KEY. 

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


> ⚠️ **Important:**  
> We **do not recommend embedding your OpenAI API key inside the Docker image**.  
> Always run the container locally where you can safely manage environment variables.  
> If you maintain a **private Docker registry**, you can build and push your own image using:
> ```bash
> docker build -t <your-registry>/deda:latest .
> docker push <your-registry>/deda:latest
> ```
> Please contact us for assistance if you’d like to set up private image hosting.

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

---

## ✅ 4. Summary

| Mode | Command | Notes |
|------|----------|-------|
| **Local Docker (recommended)** | `helm install deda ./deda` | Keeps API key private |
| **KIND cluster** | `kind load docker-image deda:latest` → `helm install deda ./deda` | For Kubernetes testing |
| **Private registry** | `docker push <your-registry>/deda:latest` | Contact us for setup help |