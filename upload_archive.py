from huggingface_hub import HfApi
import os

api = HfApi()
file_path = os.path.expanduser("~/ai_arb/termux_full_backup.tar.gz")
repo_id = "palcikia111/termux-ai-arb"

print("⏳ Начинаю загрузку архива в облако (это может занять пару минут)...")
try:
    api.upload_file(
        path_or_fileobj=file_path,
        path_in_repo="termux_full_backup.tar.gz",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("✅ УСПЕХ! Архив полностью загружен в Hugging Face!")
except Exception as e:
    print(f"❌ Ошибка: {e}")
