from pathlib import Path

import yaml

# laje-signature/knowledge/chef_profile.yaml — relativo à raiz do pacote
_KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
PROFILE_PATH = _KNOWLEDGE_ROOT / "chef_profile.yaml"


def load_profile(path: Path | None = None) -> dict:
    """Carrega o perfil culinário versionado. O agente não deve alterá-lo."""
    profile_path = path or PROFILE_PATH

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Crie {profile_path} antes de iniciar o agente."
        )

    with profile_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not data or "chef_profile" not in data:
        raise ValueError(
            "chef_profile.yaml deve conter a chave de nível superior 'chef_profile'."
        )

    return data["chef_profile"]
