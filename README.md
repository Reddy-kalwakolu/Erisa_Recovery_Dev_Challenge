# ERISA Recovery - Claims Analysis Portal

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-336791?style=for-the-badge&logo=htmx&logoColor=white)
![Alpine.js](https://img.shields.io/badge/Alpine.js-8BC0D0?style=for-the-badge&logo=alpinedotjs&logoColor=black)

_A full-stack web application designed for the ERISA Recovery team to analyze, manage, and collaborate on insurance claims._

---

![Application Screenshot](https://i.imgur.com/K3aYq0R.png)

## 📋 Table of Contents

- [About The Project](#-about-the-project)
- [✨ Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [🖥️ Usage](#️-usage)
- [🧪 Running Tests](#-running-tests)
- [☁️ Deployment](#️-deployment)

---

## 📖 About The Project

This web application is a lightweight solution that provides a modern, interactive interface for tracking claim statuses, annotating records, and identifying key financial trends to maximize revenue recovery.

This project was built as a submission for the **Dev Challenge 2025**.

---

## ✨ Features

- **Secure User Authentication:** A complete registration and login system with robust validation for unique emails and interactive password strength feedback.
- **Action Center Dashboard:** A dynamic command center providing at-a-glance KPIs, prioritized work queues (High-Value Denials, Aging Claims), and a live team activity feed.
- **Interactive Claims List:**
  - **Live Search & Filtering:** Instantly search by patient, status, or insurer without full page reloads.
  - **HTMX-Powered Detail View:** Click "View" on any claim to open a detailed panel on the same page, preserving your context in the main list.
- **Collaboration Tools:**
  - **Claim Flagging:** Users can flag claims for personal review, which appear on their dashboard.
  - **Public & Private Notes:** Add timestamped notes to any claim, visible only to you or the entire team.
- **Comprehensive Audit Trail:** A complete, uneditable log of every status change for each claim.
- **Flexible Data Management:** An easy-to-use upload page to add new claims data from JSON files, with options to **append** or **overwrite**.
- **Robust Test Suite:** Comprehensive tests covering model integrity, business logic, security, and functionality.

---

## 🛠️ Tech Stack

This project was built using the specific technologies required by the development challenge:

- **Backend:** Django 5+ (Python)
- **Database:** SQLite
- **Frontend:** HTML5, Tailwind CSS (via CDN)
- **JavaScript:** HTMX & Alpine.js

---

## 🚀 Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

Make sure you have Python (version 3.8 or higher) installed on your system.

### Installation

1.  **Clone the Repository:**

    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and Activate a Virtual Environment:**

    - On Windows:
      ```bash
      python -m venv venv
      .\venv\Scripts\activate
      ```
    - On macOS / Linux:
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply Database Migrations:**
    This will create the `db.sqlite3` file and set up the necessary tables.

    ```bash
    python manage.py migrate
    ```

5.  **Load Initial Data (Required):**
    Use the custom management command to populate the database from the provided JSON files.
    ```bash
    python manage.py load_claims claims_data.json claim_details.json --mode overwrite
    ```
6.  **Create a Superuser (Optional):**
    This allows you to access the Django admin interface at `/admin/`.
    ```bash
    python manage.py createsuperuser
    ```

---

## 🖥️ Usage

To run the application locally, use the Django development server:

```bash
python manage.py runserver
```
