"""Install the exact reviewed MIT RVC dependency (source only, no model downloads)."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];target=root/"third_party/rvc"
COMMIT="81eed5e8f68b6bed1789f682fe78cdd324495afc"
if not target.exists():subprocess.run(["git","clone","https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git",str(target)],check=True)
subprocess.run(["git","-C",str(target),"checkout",COMMIT],check=True)
print("RVC dependency pinned:",COMMIT)
