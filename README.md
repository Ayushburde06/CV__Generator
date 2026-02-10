# Django CV Generator

Hi! 👋 This is a Resume Builder application I built to learn **Django** and web development. It helps users create professional resumes by filling out a simple form.

## 🛠 Tech Stack Used
- **Python** (Backend Logic)
- **Django** (Web Framework)
- **HTML/CSS** (Frontend Styling)
- **SQLite** (Database)
- **ReportLab** (For generating PDFs)

## ✨ What it does
- Users can sign up and login.
- Enter details like Education, Skills, Projects, and Certifications.
- Choose from 7 different resume templates.
- **Download the final resume as a PDF!** 📄

## 🚀 How to Run Locally

If you want to run this project on your computer:

1.  **Download the code**:
    ```bash
    git clone https://github.com/Ayushburde06/CV__Generator.git
    cd CV__Generator
    ```

2.  **Set up the environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate   # On Windows
    # source venv/bin/activate  # On Mac/Linux
    ```

3.  **Install libraries**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the app**:
    ```bash
    python manage.py runserver
    ```

5.  Open the link in your browser: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 📸 Screenshots

![Home Page](screenshots/home.png)
*Home Page*

![Form Section](screenshots/form.png)
*Entering Details*

![Resume Preview](screenshots/preview.png)
*Final Resume PDF*
