from huggingface_hub import HfApi

print("⏳ Создаю репозиторий в облаке Hugging Face...")
try:
    api = HfApi()
    url = api.create_repo(
        repo_id="palcikia111/termux-ai-arb", 
        repo_type="dataset", 
        private=True
    )
    print(f"✅ УСПЕХ! Репозиторий создан: {url}")
except Exception as e:
    print(f"⚠️ Ошибка: {e}")
