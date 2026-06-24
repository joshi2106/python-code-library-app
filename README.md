 Digital Library Project

A simple microservices-based Digital Library application built with **Python Flask**, containerized using **Docker**, and deployed on **AWS ECS Fargate** behind an **Application Load Balancer (ALB)**.

---

## 📖 What the App Does
- Users can **sign up** and **sign in**
- Browse available **books**
- **Borrow books** and view borrowed books
- Frontend shows HTML pages and calls backend services

---

## 🏗️ Architecture
Internet
│
▼
[ALB: library-alb] (HTTP:80, public)
├── /auth*   → auth-service (port 5001)
├── /books*  → book-service (port 5002)
├── /borrow* → borrow-service (port 5003)
└── default  → frontend (port 5000)

**#RDS MySQL (private subnet)**

- **Frontend** → Renders HTML, talks to other services  
- **Auth Service** → Signup, signin, password hashing  
- **Book Service** → List books, get single book  
- **Borrow Service** → Borrow books, view borrowed books  

---

## 📂 Repository Structure
python-code-library-app/
├── .github/workflows/image-build-push.yml   # CI/CD pipeline
├── auth/ (auth_service.py, Dockerfile, requirements.txt)
├── book/ (book_service.py, Dockerfile, requirements.txt)
├── borrow/ (borrow_service.py, Dockerfile, requirements.txt)
├── templates/ (HTML files)
├── database/schema.sql
├── Dockerfile (frontend)
├── app.py (frontend code)
└── requirements.txt (frontend dependencies)



---

## ⚙️ CI/CD Pipeline
- Trigger: push to `master`
- Builds all 4 Docker images in parallel
- Runs **Trivy security scan**
- Tags images with commit SHA + `latest`
- Pushes to **Amazon ECR**
- AWS credentials injected via **OIDC** (no long-lived keys)

---

## 🔐 Secrets & Environment Variables
- Stored in **AWS SSM Parameter Store** or **Secrets Manager**
- Example:
  - `/library/prod/DB_HOST` → SecureString
  - `/library/prod/DB_USER` → Secrets Manager
  - `/library/prod/DB_PASSWORD` → Secrets Manager
  - `/library/prod/DB_NAME` → String
  - `/library/prod/ALB_URL` → String
  - `/library/prod/SECRET_KEY` → SecureString (frontend only)

⚠️ **Important:** `.env` files do **not** work in ECS. Use SSM or Secrets Manager.

---

## 🔒 Security
- **Security Groups**
  - `alb-sg`: allow HTTP 80 from anywhere
  - `ecs-sg`: allow ports 5000–5003 only from ALB
  - `rds-sg`: allow MySQL 3306 only from ECS
- Traffic flow: Internet → ALB → ECS → RDS

---

## 🗄️ Database
- **RDS MySQL 8.0** in private subnet
- Tables:
  - `users`
  - `books`
  - `borrow_records` (unique constraint on user_id + book_id)

---

## 📊 Monitoring
- Logs stored in **CloudWatch**:
  - `/ecs/library-frontend`
  - `/ecs/library-auth`
  - `/ecs/library-book`
  - `/ecs/library-borrow`

---

## ✅ Health Check URLs
- Frontend → `http://ALB_DNS/health`
- Auth → `http://ALB_DNS/auth/health`
- Book → `http://ALB_DNS/books/health`
- Borrow → `http://ALB_DNS/borrow/health`

---

## 🚀 Deployment Notes
- ECS Fargate cluster: `library-cluster`
- Each service has its own **task definition** and **ECS service**
- Connected to ALB target groups with path-based routing

---

## 🔑 Quick Reference
- **Frontend** → needs `ALB_URL`, `SECRET_KEY`
- **Auth/Book/Borrow** → need `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- **SECRET_KEY** is mandatory for session security in Flask

---

## 📅 Project Status
- Completed: June 25, 2026
- Stack: Python Flask · Docker · GitHub Actions · AWS ECS Fargate · ALB · RDS MySQL · SSM Parameter Store · CloudWatch · ECR
