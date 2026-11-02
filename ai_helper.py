import sys
from pathlib import Path
sys.path.append(str(Path.home() / 'quantum_lab_sandbox' / 'tools' / 'agent_dev'))
try:
    from llm_backend import ask
    prompt = sys.stdin.read()
    result = ask(prompt, system_prompt="Ты — агент парсинга. Отвечай СТРОГО в формате JSON без лишнего текста.")
    print(result)
except Exception as e:
    print('{"error": "' + str(e).replace('"', "'") + '"}', file=sys.stdout)
