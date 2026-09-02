from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from src.core.constants import ExperienceLevel
from src.database.database import get_session
from src.database.models import User


class ProfileTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.user_id: int | None = None

        self.name_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        self.experience_combo = QComboBox()
        self.experience_combo.addItem("-", None)
        for level in ExperienceLevel:
            self.experience_combo.addItem(level.value, level)

        self.linkedin_edit = QLineEdit()
        self.linkedin_edit.setPlaceholderText("https://linkedin.com/in/seu-usuario")
        self.portfolio_edit = QLineEdit()
        self.portfolio_edit.setPlaceholderText("https://seuportfolio.com")

        self.desired_roles_edit = QLineEdit()
        self.desired_roles_edit.setPlaceholderText("Ex: Desenvolvedor Backend, Engenheiro de Software")
        self.salary_expectation_edit = QLineEdit()
        self.salary_expectation_edit.setPlaceholderText("Ex: R$ 6.000 - R$ 8.000")
        self.languages_edit = QLineEdit()
        self.languages_edit.setPlaceholderText("Ex: Portugues (nativo), Ingles (avancado)")

        self.resume_path_edit = QLineEdit()
        self.resume_path_edit.setReadOnly(True)
        resume_button = QPushButton("Selecionar arquivo...")
        resume_button.clicked.connect(self._pick_resume)

        self.skills_edit = QPlainTextEdit()
        self.skills_edit.setPlaceholderText(
            "Liste suas competencias tecnicas separadas por virgula - usado para checar se a LLM "
            "nao inventa nada ao adaptar o curriculo. Ex: Python, FastAPI, PostgreSQL, Docker, Git"
        )
        self.skills_edit.setFixedHeight(70)

        self.profile_summary_edit = QPlainTextEdit()
        self.profile_summary_edit.setPlaceholderText(
            "Descreva experiencia, contexto de carreira e tecnologias - usado para pontuar as vagas."
        )
        self.profile_summary_edit.setFixedHeight(100)

        save_button = QPushButton("Salvar")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Nome", self.name_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Telefone", self.phone_edit)
        form.addRow("Nivel", self.experience_combo)
        form.addRow("LinkedIn", self.linkedin_edit)
        form.addRow("Portfolio / GitHub", self.portfolio_edit)
        form.addRow("Cargos desejados", self.desired_roles_edit)
        form.addRow("Pretensao salarial", self.salary_expectation_edit)
        form.addRow("Idiomas", self.languages_edit)
        form.addRow("Curriculo", self.resume_path_edit)
        form.addRow("", resume_button)
        form.addRow(QLabel("Competencias (para validar o curriculo adaptado)"))
        form.addRow(self.skills_edit)
        form.addRow(QLabel("Resumo do perfil"))
        form.addRow(self.profile_summary_edit)

        form_widget = QWidget()
        form_widget.setLayout(form)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setWidget(form_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(scroll_area, 1)
        layout.addWidget(save_button)

        self._load()

    def _load(self) -> None:
        with get_session() as session:
            user = session.execute(select(User)).scalars().first()
            if user is None:
                return

            self.user_id = user.id
            self.name_edit.setText(user.name)
            self.email_edit.setText(user.email)
            self.phone_edit.setText(user.phone or "")
            self.linkedin_edit.setText(user.linkedin_url or "")
            self.portfolio_edit.setText(user.portfolio_url or "")
            self.desired_roles_edit.setText(user.desired_roles or "")
            self.salary_expectation_edit.setText(user.salary_expectation or "")
            self.languages_edit.setText(user.languages or "")
            self.resume_path_edit.setText(user.resume_path or "")
            self.skills_edit.setPlainText(user.skills or "")
            self.profile_summary_edit.setPlainText(user.profile_summary or "")

            index = self.experience_combo.findData(user.experience_level)
            if index >= 0:
                self.experience_combo.setCurrentIndex(index)

    def _pick_resume(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar curriculo", "", "Documentos (*.pdf *.docx)")
        if path:
            self.resume_path_edit.setText(path)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        email = self.email_edit.text().strip()

        if not name or not email:
            QMessageBox.warning(self, "Dados incompletos", "Nome e email sao obrigatorios.")
            return

        with get_session() as session:
            if self.user_id is not None:
                user = session.get(User, self.user_id)
            else:
                user = User(email=email)
                session.add(user)

            user.name = name
            user.email = email
            user.phone = self.phone_edit.text().strip() or None
            user.experience_level = self.experience_combo.currentData()
            user.linkedin_url = self.linkedin_edit.text().strip() or None
            user.portfolio_url = self.portfolio_edit.text().strip() or None
            user.desired_roles = self.desired_roles_edit.text().strip() or None
            user.salary_expectation = self.salary_expectation_edit.text().strip() or None
            user.languages = self.languages_edit.text().strip() or None
            user.resume_path = self.resume_path_edit.text().strip() or None
            user.skills = self.skills_edit.toPlainText().strip() or None
            user.profile_summary = self.profile_summary_edit.toPlainText().strip() or None
            session.flush()
            self.user_id = user.id

        QMessageBox.information(self, "Perfil salvo", "Perfil salvo com sucesso.")
