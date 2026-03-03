# NightOwl Modules Package
# Modules d'attaque simulée pour tests Red Team

__version__ = "1.0.0"
__author__ = "NightOwl Security Team"
__license__ = "MIT - Usage restreint aux tests autorisés"

# Import des modules disponibles
from .reconnaissance import ReconnaissanceModule
from .privilege_escalation import PrivilegeEscalationModule
from .lateral_movement import LateralMovementModule
from .persistence import PersistenceModule
from .defense_evasion import DefenseEvasionModule