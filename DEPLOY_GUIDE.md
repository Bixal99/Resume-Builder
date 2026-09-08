# 🚀 Deploying ResuMate Online

This guide explains how to push **ResuMate** to your GitHub repository and deploy it online for free so anyone can use it.

---

## Part 1: Push to GitHub

Follow these steps to upload your project to GitHub:

### Step 1.1: Create a GitHub Repository
1. Log in to your account on [GitHub](https://github.com/).
2. Click the **New** button (or go to [github.com/new](https://github.com/new)).
3. Fill in:
   - **Repository name**: `ResuMate`
   - **Description** (Optional): `Professional Resume Builder application.`
   - **Public/Private**: Select **Public** so others can see and use your product.
   - **Initialize options**: **Do NOT check** README, .gitignore, or license boxes (we already have these in the project).
4. Click **Create repository**.

### Step 1.2: Run Pushing Commands
Open your terminal (PowerShell or Command Prompt) in `D:\My_products\ResuMate` and run these two commands:

```bash
# 1. Link your local project to your newly created GitHub repository
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/ResuMate.git

# 2. Push the code to the main branch
git push -u origin main
```
*(Make sure to replace `YOUR_GITHUB_USERNAME` with your actual GitHub username!)*

---

## Part 2: Deploy Free on Render.com

Since GitHub Pages only hosts static websites (HTML/CSS) and cannot run a Python/FastAPI backend, we will deploy it on **Render.com** (which is completely free and automatically builds and hosts your app using the existing Dockerfile).

### Step 2.1: Sign Up on Render
1. Go to [Render.com](https://render.com/).
2. Click **Sign Up** and choose **GitHub** to log in directly.

### Step 2.2: Create a Web Service
1. On your Render dashboard, click the blue **New +** button and select **Web Service**.
2. Under **Connect a repository**, find your `ResuMate` repository and click **Connect**.

### Step 2.3: Configure Settings
Set the following options on the configuration page:
- **Name**: `resumate`
- **Language**: Select **Docker** (Render will automatically read the `Dockerfile` in the project).
- **Instance Type**: Select **Free** (0$ / month).

### Step 2.4: Add Environment Variables
Scroll down and click **Advanced** -> **Add Environment Variable**:
- Key: `DEBUG` | Value: `false`
- Key: `PORT` | Value: `8000`
- Key: `SECRET_KEY` | Value: `some-long-random-string-here`

### Step 2.5: Deploy!
- Click **Create Web Service** at the bottom of the page.
- Render will start building the Docker image (which automatically installs Python, Playwright, Chromium, and WeasyPrint).
- Once the build is complete (usually 4-5 minutes), Render will display a link at the top left (e.g., `https://resumate.onrender.com`). Share this link with anyone so they can build their resumes!

---

## Part 3: Run directly in browser via GitHub Codespaces

Anyone viewing your GitHub repository can also run the app for free with one click using GitHub Codespaces:

1. On your GitHub repository page, click the green **Code** button.
2. Select the **Codespaces** tab.
3. Click **Create codespace on main**.
4. Once it opens, open the terminal in the browser and run:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
5. Click **Open in Browser** on the pop-up notification to use the app!
