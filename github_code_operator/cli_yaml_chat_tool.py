#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive CLI tool for chatting with LLM to modify YAML files in GitHub repos
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from github import Github
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any

class YAMLChatTool:
    def __init__(self, github_token: str, openai_key: str, repo_name: str = None):
        self.github = Github(github_token) if github_token else None
        # LLM client is constructed per request via ChatOpenAI now
        self.openai_client = None
        self.repo = None
        self.working_dir = Path.cwd()
        
        if repo_name and self.github:
            self.repo = self.github.get_repo(repo_name)
    
    def find_local_yaml_files(self, criteria: Dict) -> List[Path]:
        """Find YAML files in local directory based on criteria"""
        yaml_files = []
        
        for root, dirs, files in os.walk(self.working_dir):
            for file in files:
                if file.endswith(('.yml', '.yaml')):
                    file_path = Path(root) / file
                    if self._matches_criteria(file_path, criteria):
                        yaml_files.append(file_path)
        
        return yaml_files

    def find_github_yaml_files(self, criteria: Dict) -> List[Dict[str, Any]]:
        """Find YAML files in the connected GitHub repo based on criteria.

        Returns a list of dicts with keys: path, name, sha, size
        """
        if not self.repo:
            return []

        matching_files: List[Dict[str, Any]] = []

        try:
            contents = self.repo.get_contents("")
            while contents:
                file_content = contents.pop(0)
                if getattr(file_content, "type", None) == "dir":
                    contents.extend(self.repo.get_contents(file_content.path))
                    continue

                path_parts = tuple(Path(file_content.path).parts)

                # Extension filter
                if not (file_content.path.endswith(".yml") or file_content.path.endswith(".yaml")):
                    continue

                # Required directories
                if "required_dirs" in criteria:
                    if any(req not in path_parts for req in criteria["required_dirs"]):
                        continue

                # Excluded directories
                if "excluded_dirs" in criteria:
                    if any(exc in path_parts for exc in criteria["excluded_dirs"]):
                        continue

                # Filename pattern (substring match)
                if "filename_pattern" in criteria:
                    if criteria["filename_pattern"] not in Path(file_content.path).name:
                        continue

                matching_files.append({
                    "path": file_content.path,
                    "name": file_content.name,
                    "sha": file_content.sha,
                    "size": getattr(file_content, "size", None),
                })

        except Exception:
            # Be conservative; on API failure, return empty list so caller can handle
            return []

        return matching_files
    
    def _matches_criteria(self, file_path: Path, criteria: Dict) -> bool:
        """Check if file matches the given criteria"""
        relative_path = file_path.relative_to(self.working_dir)
        path_parts = relative_path.parts
        
        # Check required directories
        if 'required_dirs' in criteria:
            for req_dir in criteria['required_dirs']:
                if req_dir not in path_parts:
                    return False
        
        # Check excluded directories
        if 'excluded_dirs' in criteria:
            for exc_dir in criteria['excluded_dirs']:
                if exc_dir in path_parts:
                    return False
        
        # Check filename pattern
        if 'filename_pattern' in criteria:
            if criteria['filename_pattern'] not in file_path.name:
                return False
        
        # Check file size (avoid huge files)
        if file_path.stat().st_size > 100000:  # 100KB limit
            return False
            
        return True
    
    def chat_with_llm(self, user_message: str, file_context: Dict) -> Dict:
        """Get LLM response for YAML modification"""
        system_prompt = """
        You are an expert YAML file modification assistant. Users will describe changes they want to make to YAML files.
        
        Analyze the request and respond with a JSON object:
        {
            "understood": true/false,
            "property_path": "dot.separated.path.to.property",
            "property_value": actual_value (string, number, boolean, array, or object),
            "action": "add" | "modify" | "delete",
            "reasoning": "Clear explanation of what you're doing and why",
            "questions": ["any clarification questions if needed"]
        }
        
        Rules:
        1. If the request is unclear, set "understood": false and ask questions
        2. Property paths use dot notation: "server.config.timeout"
        3. Property values should be the correct type (not always string)
        4. Be conservative - if unsure, ask for clarification
        5. Consider the existing file structure when suggesting paths
        """
        
        # Prepare file context
        context_str = f"""
        File: {file_context['path']}
        Current structure preview:
        {file_context['preview']}
        """
        
        # Build a single prompt string. ChatOpenAI expects strings or LC message objects.
        prompt = (
            f"{system_prompt}\n\n"
            f"{context_str}\n\n"
            f"User request: {user_message}\n\n"
            f"Respond ONLY with a valid JSON object per the schema."
        )

        llm = ChatOpenAI(
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.0,
        )
        try:
            response = llm.invoke(prompt)
            content = getattr(response, "content", None)
            if not content:
                return {"error": "Empty response from LLM"}
            return json.loads(content)
        except json.JSONDecodeError as e:
            raw = content if isinstance(content, str) else str(content)
            return {"error": f"Could not parse LLM response: {e}", "raw_response": raw}
        except Exception as e:
            return {"error": f"LLM request failed: {e}"}
    
    def preview_yaml_structure(self, yaml_content: str, max_lines: int = 20) -> str:
        """Create a preview of YAML structure"""
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                return "Empty YAML file"
            
            def get_structure(obj, prefix="", depth=0):
                if depth > 3:  # Limit depth
                    return []
                    
                lines = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"{prefix}{key}:")
                            if depth < 2:  # Only go deeper for shallow objects
                                lines.extend(get_structure(value, prefix + "  ", depth + 1))
                        else:
                            lines.append(f"{prefix}{key}: {type(value).__name__}")
                elif isinstance(obj, list) and obj:
                    lines.append(f"{prefix}- {type(obj[0]).__name__} (array of {len(obj)} items)")
                
                return lines
            
            structure_lines = get_structure(data)
            return "\n".join(structure_lines[:max_lines])
            
        except Exception as e:
            return f"Could not parse YAML: {e}"

    def modify_yaml_content(self, yaml_content: str, property_path: str, property_value: Any, action: str) -> tuple:
        """Modify YAML content string and return (original_content, modified_content, error)."""
        try:
            original_content = yaml_content
            data = yaml.safe_load(yaml_content) or {}

            # Navigate to property location
            path_parts = property_path.split('.')
            current = data

            # Create nested structure if needed
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    return None, None, f"Path conflict: {part} is not a dictionary"
                current = current[part]

            final_key = path_parts[-1]
            if action in ("add", "modify"):
                current[final_key] = property_value
            elif action == "delete":
                if final_key in current:
                    del current[final_key]
                else:
                    return None, None, f"Property {final_key} not found for deletion"

            modified_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return original_content, modified_content, None
        except Exception as e:
            return None, None, f"Error modifying YAML content: {e}"
    
    def modify_yaml_file(self, file_path: Path, property_path: str, property_value: Any, action: str) -> tuple:
        """Modify a YAML file"""
        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = yaml.safe_load(content) or {}
            
            # Navigate to property location
            path_parts = property_path.split('.')
            current = data
            
            # Create nested structure if needed
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    return None, f"Path conflict: {part} is not a dictionary"
                current = current[part]
            
            # Apply the change
            final_key = path_parts[-1]
            
            if action == "add" or action == "modify":
                current[final_key] = property_value
            elif action == "delete":
                if final_key in current:
                    del current[final_key]
                else:
                    return None, f"Property {final_key} not found for deletion"
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            return content, None  # Return original content for backup
            
        except Exception as e:
            return None, f"Error modifying {file_path}: {e}"

    def _manual_collect_change(self) -> Dict[str, Any]:
        """Fallback: prompt user to specify change details manually."""
        print("   ⚙️  Manual mode: enter change details")
        while True:
            action = input("   Action (add/modify/delete): ").strip().lower()
            if action in ("add", "modify", "delete"):
                break
            print("   Please enter 'add', 'modify', or 'delete'.")

        property_path = input("   Property path (dot.notation): ").strip()
        property_value: Any = None
        if action in ("add", "modify"):
            raw_value = input('   Value (JSON, e.g. true, 123, "text", {"k":1}): ').strip()
            try:
                property_value = json.loads(raw_value)
            except Exception:
                # treat as string if not valid JSON
                property_value = raw_value

        return {
            "understood": True,
            "action": action,
            "property_path": property_path,
            "property_value": property_value,
            "reasoning": "Manual user-specified change"
        }
    
    def interactive_chat(self):
        """Main interactive chat loop"""
        print("🤖 YAML Chat Tool - Interactive Mode")
        print("Type 'quit' to exit, 'help' for commands")
        print("-" * 50)
        
        # Get search criteria
        criteria = self._get_search_criteria()
        
        # Find files (prefer GitHub if repo is configured)
        if self.repo:
            github_files = self.find_github_yaml_files(criteria)
            yaml_files = github_files  # List of dicts
            use_github = True
        else:
            yaml_files = self.find_local_yaml_files(criteria)  # List of Paths
            use_github = False
        
        if not yaml_files:
            print("❌ No YAML files found matching criteria")
            return
        
        print(f"✅ Found {len(yaml_files)} matching files:")
        for i, file_item in enumerate(yaml_files, 1):
            if use_github:
                print(f"  {i}. {file_item['path']}")
            else:
                rel_path = file_item.relative_to(self.working_dir)
                print(f"  {i}. {rel_path}")
        
        print("\n" + "="*50)
        
        while True:
            try:
                user_input = input("\n💬 Your request: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'files':
                    self._show_files(yaml_files, use_github)
                    continue
                elif not user_input:
                    continue
                
                # Process the request
                self._process_request(user_input, yaml_files, use_github)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _get_search_criteria(self) -> Dict:
        """Get search criteria from user"""
        print("\n📁 Define search criteria for YAML files:")
        
        criteria = {}
        
        # Required directories
        req_dirs = input("Required directories (comma-separated, optional): ").strip()
        if req_dirs:
            criteria['required_dirs'] = [d.strip() for d in req_dirs.split(',')]
        
        # Filename pattern
        filename_pattern = input("Filename must contain (optional): ").strip()
        if filename_pattern:
            criteria['filename_pattern'] = filename_pattern
        
        # Excluded directories
        exc_dirs = input("Exclude directories (comma-separated, optional): ").strip()
        if exc_dirs:
            criteria['excluded_dirs'] = [d.strip() for d in exc_dirs.split(',')]
        
        return criteria
    
    def _process_request(self, user_request: str, yaml_files: List[Any], use_github: bool):
        """Process a user request for all matching files"""
        print(f"\n🔄 Processing request: {user_request}")
        
        successful_changes = 0
        
        for file_item in yaml_files:
            try:
                # Read file and create context
                if use_github:
                    gh_file = self.repo.get_contents(file_item["path"])  # fresh fetch for latest
                    content = gh_file.decoded_content.decode('utf-8')
                    file_context = {
                        'path': file_item['path'],
                        'preview': self.preview_yaml_structure(content)
                    }
                else:
                    file_path = file_item
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    file_context = {
                        'path': str(file_path.relative_to(self.working_dir)),
                        'preview': self.preview_yaml_structure(content)
                    }
                
                # Get LLM response
                llm_response = self.chat_with_llm(user_request, file_context)
                
                if 'error' in llm_response:
                    print(f"❌ {Path(file_context['path']).name}: {llm_response['error']}")
                    use_manual = input("   Enter details manually? (y/N): ").strip().lower() == 'y'
                    if not use_manual:
                        continue
                    llm_response = self._manual_collect_change()
                
                if not llm_response.get('understood', True):
                    print(f"❓ {Path(file_context['path']).name}: Need clarification")
                    if 'questions' in llm_response:
                        for q in llm_response['questions']:
                            print(f"   - {q}")
                    use_manual = input("   Enter details manually? (y/N): ").strip().lower() == 'y'
                    if not use_manual:
                        continue
                    llm_response = self._manual_collect_change()
                
                # Show what will be changed
                print(f"\n📝 {Path(file_context['path']).name}:")
                print(f"   Action: {llm_response['action']}")
                print(f"   Property: {llm_response['property_path']}")
                print(f"   Value: {llm_response['property_value']}")
                print(f"   Reason: {llm_response['reasoning']}")
                
                # Ask for confirmation
                confirm = input("   Apply this change? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("   ⏭️  Skipped")
                    continue
                
                # Apply the change
                if use_github:
                    original, modified, error = self.modify_yaml_content(
                        content,
                        llm_response['property_path'],
                        llm_response['property_value'],
                        llm_response['action']
                    )
                else:
                    backup_content, error = self.modify_yaml_file(
                        file_path,
                        llm_response['property_path'],
                        llm_response['property_value'],
                        llm_response['action']
                    )
                
                if error:
                    print(f"   ❌ Error: {error}")
                else:
                    if use_github:
                        # Commit back to GitHub
                        try:
                            latest = self.repo.get_contents(file_item['path'])
                            self.repo.update_file(
                                latest.path,
                                f"Update {Path(latest.path).name}: {llm_response['reasoning']}",
                                modified,
                                latest.sha
                            )
                            print("   ✅ Changed successfully (committed to GitHub)")
                        except Exception as e:
                            print(f"   ❌ GitHub update failed: {e}")
                            continue
                    else:
                        print(f"   ✅ Changed successfully")
                    successful_changes += 1
                
            except Exception as e:
                print(f"❌ {Path(file_context['path']).name}: Unexpected error: {e}")
        
        print(f"\n🎉 Successfully modified {successful_changes}/{len(yaml_files)} files")
    
    def _show_help(self):
        """Show help information"""
        print("""
Commands:
  - help: Show this help
  - files: List found YAML files again
  - quit/exit/q: Exit the tool

Example requests:
  - "Add a timeout property with value 30 seconds"
  - "Set the database host to localhost"
  - "Remove the debug flag"
  - "Add a new service configuration with port 8080"
        """)
    
    def _show_files(self, yaml_files: List[Any], use_github: bool):
        """Show the list of found files"""
        print(f"\nFound {len(yaml_files)} YAML files:")
        for i, file_item in enumerate(yaml_files, 1):
            if use_github:
                print(f"  {i}. {file_item['path']}")
            else:
                rel_path = file_item.relative_to(self.working_dir)
                print(f"  {i}. {rel_path}")

def main():
    parser = argparse.ArgumentParser(description="Interactive YAML modification with LLM")
    parser.add_argument("--github-token", help="GitHub personal access token")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--repo", help="GitHub repository (owner/repo)")
    
    args = parser.parse_args()
    
    # Get API keys from environment if not provided
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    openai_key = args.openai_key or os.getenv('OPENAI_API_KEY')
    
    if not openai_key:
        print("❌ OpenAI API key required (--openai-key or OPENAI_API_KEY env var)")
        sys.exit(1)
    
    tool = YAMLChatTool(github_token, openai_key, args.repo)
    tool.interactive_chat()

if __name__ == "__main__":
    main()