from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
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

        self.resume_path_edit = QLineEdit()
        self.resume_path_edit.setReadOnly(True)
        resume_button = QPushButton("Selecionar arquivo...")
        resume_button.clicked.connect(self._pick_resume)

        self.profile_summary_edit = QPlainTextEdit()
        self.profile_summary_edit.setPlaceholderText(
            "Descreva skills, experiencia e tecnologias - isso e usado para pontuar as vagas."
        )

        save_button = QPushButton("Salvar")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Nome", self.name_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Telefone", self.phone_edit)
        form.addRow("Nivel", self.experience_combo)
        form.addRow("Curriculo", self.resume_path_edit)
        form.addRow("", resume_button)
        form.addRow(QLabel("Resumo do perfil"))
        form.addRow(self.profile_summary_edit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(save_button)
        layout.addStretch()

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
            self.resume_path_edit.setText(user.resume_path or "")
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
            user.resume_path = self.resume_path_edit.text().strip() or None
            user.profile_summary = self.profile_summary_edit.toPlainText().strip() or None
            session.flush()
            self.user_id = user.id

        QMessageBox.information(self, "Perfil salvo", "Perfil salvo com sucesso.")
