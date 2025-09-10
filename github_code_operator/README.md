# Introduction 
Interact with github code repo and may modify some files by LLM model.

# Preparation
```shell
python3 -m venv .venv
source .venv/bin/activate
pip3 install uv
uv pip install -r requirements.txt
```
then create .env file add github token and openai like llm token

# one shot command to add a property
```shell
source .venv/bin/activate && python -m py_compile github_code_operator/cli_yaml_chat_tool.py && set -a; source .env
; set +a; printf "\n\n\nadd a property named 'demo.address' with the value 'aaa street'\ny\nadd\ndemo.address\n\"aaa street\"\ny\nquit\n" | python github_code_operator/cli_yaml_chat_tool.py --repo "shayne007/langGraph-demo" | cat
```