from PySide6.QtWidgets import(
	QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel
)

class MainWindows(QWidget):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Gestion des fertilisants")

		layout = QVBoxLayout()

		self.nom = QLineEdit()
		self.nom.setPlaceholderText("Nom du fertilisant")

		self.dose = QLineEdit()
		self.dose.setPlaceholderText("Dose kg/ha")

		btn = QPushButton("Enregistrer")

		layout.addWidget(QLabel("Ajouter une fertilisant"))
		layout.addWidget(self.nom)
		layout.addWidget(self.dose)
		layout.addWidget(btn)
		self.setLayout(layout)