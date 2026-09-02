from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QTextEdit, QVBoxLayout

from src.core.constants import ExperienceLevel, WorkMode
from src.database.models import Vacancy

EXPERIENCE_LABELS = {
    ExperienceLevel.INTERN: "Estagio/Trainee",
    ExperienceLevel.JUNIOR: "Junior",
    ExperienceLevel.MID: "Pleno",
    ExperienceLevel.SENIOR: "Senior",
    ExperienceLevel.LEAD: "Lideranca",
}

WORK_MODE_LABELS = {
    WorkMode.REMOTE: "Remoto",
    WorkMode.HYBRID: "Hibrido",
    WorkMode.ONSITE: "Presencial",
}


class VacancyDetailDialog(QDialog):
    def __init__(self, vacancy: Vacancy, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(vacancy.title)
        self.resize(600, 500)

        form = QFormLayout()
        form.addRow("Empresa", QLabel(vacancy.company))
        form.addRow("Local", QLabel(vacancy.location or "Nao informado"))
        form.addRow("Modalidade", QLabel(WORK_MODE_LABELS.get(vacancy.work_mode, "Nao informado")))
        form.addRow("Nivel", QLabel(EXPERIENCE_LABELS.get(vacancy.experience_level, "Nao informado")))
        form.addRow("Salario", QLabel(vacancy.salary_range or "Nao informado"))
        form.addRow("Fonte", QLabel(vacancy.source.value))
        form.addRow("Score", QLabel(
            f"{vacancy.compatibility_score:.2f}" if vacancy.compatibility_score is not None else "Nao pontuada"
        ))

        description_label = QLabel("Descricao / Requisitos / Beneficios")

        self.description_edit = QTextEdit()
        self.description_edit.setReadOnly(True)
        self.description_edit.setPlainText(
            vacancy.description or "Nenhuma descricao disponivel para esta vaga."
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(description_label)
        layout.addWidget(self.description_edit, 1)
