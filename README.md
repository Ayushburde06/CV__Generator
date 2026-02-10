# CV Generator

A powerful, user-friendly web application built with **Django** to create professional Curriculum Vitae (CV) / Resumes in PDF format.

## 🚀 Features

- **Multi-Step Form**: Easy-to-use wizard for entering personal info, summary, projects, skills, education, and certifications.
- **7 Professional Templates**: Choose from Classic, Modern, Minimal, Professional, AltaCV, CurVe, and Hipster styles.
- **Live Preview**: See your CV update in real-time as you enter data.
- **PDF Generation**: High-quality PDF export using ReportLab.
- **Customizable**: Add unlimited projects and education entries.
- **Responsive**: Works on desktop and mobile.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Ayushburde06/CV__Generator.git
    cd CV__Generator
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Start the server**:
    ```bash
    python manage.py runserver
    ```

6.  Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## 📝 Usage

1.  **Sign Up / Login** to save your progress.
2.  **Choose a Template** to start.
3.  **Fill out the form** (Personal Info, Summary, Projects, Skills, Education, Certifications).
4.  **Preview** your CV at the end.
5.  **Download PDF** and share!

## ☁️ Deployment

See [README_DEPLOY.md](README_DEPLOY.md) for instructions on deploying to Render, Railway, or Heroku.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.
