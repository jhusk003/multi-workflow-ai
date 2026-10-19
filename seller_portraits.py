"""Local referenced portraits for Jordan and Taylor; other two profiles retain existing art."""
from pathlib import Path
import base64

def embedded_portrait(name):
    path = Path(__file__).resolve().parent / 'assistant_assets' / (name.lower() + '.jpg')
    return 'data:image/jpeg;base64,' + base64.b64encode(path.read_bytes()).decode('ascii')
