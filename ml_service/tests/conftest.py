import sys
from pathlib import Path

# Добавляем корень проекта (папку ml_service) в пути поиска
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))