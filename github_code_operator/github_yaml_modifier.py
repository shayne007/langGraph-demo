import os
import yaml
import json
from github import Github
from pathlib import Path
import openai  # or any other LLM client

class GitHubYAMLModifier:
    def __init__(self, github_token, openai_api_key, repo_name):
        self.github = Github(github_token)
        self.repo = self.github.get_repo(repo_name)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
    def find_files_by_criteria(self, criteria):
        """
        Find files based on criteria like directory existence and filename patterns
        """
        matching_files = []
        
        # Get all contents recursively
        contents = self.repo.get_contents("")
        
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self.repo.get_contents(file_content.path))
            else:
                # Check if file matches criteria
                if self._matches_criteria(file_content, criteria):
                    matching_files.append(file_content)
                    
        return matching_files
    
    def _matches_criteria(self, file_content, criteria):
        """
        Check if a file matches the given criteria
        """
        file_path = Path(file_content.path)
        
        # Check filename pattern
        if 'filename_pattern' in criteria:
            if not file_path.name.endswith(criteria['filename_pattern']):
                return False
                
        # Check if required directories exist in path
        if 'required_directories' in criteria:
            path_parts = file_path.parts
            for required_dir in criteria['required_directories']:
                if required_dir not in path_parts:
                    return False
                    
        # Check file extension for YAML files
        if file_path.suffix not in ['.yaml', '.yml']:
            return False
            
        return True
    
    def chat_with_llm(self, user_message, file_context):
        """
        Chat with LLM to determine what changes to make
        """
        system_prompt = """
        You are a YAML file modification assistant. The user will describe what property they want to add to YAML files.
        
        Respond with a JSON object containing:
        {
            "property_path": "path.to.property",
            "property_value": "value to set",
            "action": "add" | "modify" | "delete",
            "reasoning": "explanation of what you're doing"
        }
        
        If the user's request is unclear, ask for clarification.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"File context: {file_context}\n\nUser request: {user_message}"}
        ]
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.1
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"error": "Could not parse LLM response", "raw_response": response.choices[0].message.content}
    
    def modify_yaml_property(self, yaml_content, property_path, property_value, action="add"):
        """
        Modify YAML content by adding/modifying a property
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return None, f"YAML parsing error: {e}"
        
        # Navigate to the property path
        path_parts = property_path.split('.')
        current = data
        
        # Navigate to parent of target property
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Perform the action
        final_key = path_parts[-1]
        if action == "add" or action == "modify":
            current[final_key] = property_value
        elif action == "delete" and final_key in current:
            del current[final_key]
        
        # Convert back to YAML
        try:
            modified_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
            return modified_yaml, None
        except yaml.YAMLError as e:
            return None, f"YAML serialization error: {e}"
    
    def process_chat_request(self, user_message, criteria):
        """
        Main method to process a chat request
        """
        # Find matching files
        matching_files = self.find_files_by_criteria(criteria)
        
        if not matching_files:
            return {"error": "No files found matching the criteria"}
        
        results = []
        
        for file_content in matching_files:
            # Get current file content
            current_content = file_content.decoded_content.decode('utf-8')
            
            # Chat with LLM to determine changes
            file_context = {
                "filename": file_content.name,
                "path": file_content.path,
                "current_content": current_content[:1000] + "..." if len(current_content) > 1000 else current_content
            }
            
            llm_response = self.chat_with_llm(user_message, file_context)
            
            if "error" in llm_response:
                results.append({
                    "file": file_content.path,
                    "error": llm_response["error"]
                })
                continue
            
            # Modify the YAML
            modified_content, error = self.modify_yaml_property(
                current_content,
                llm_response["property_path"],
                llm_response["property_value"],
                llm_response["action"]
            )
            
            if error:
                results.append({
                    "file": file_content.path,
                    "error": error
                })
                continue
            
            # Update the file in GitHub (create a new commit)
            try:
                self.repo.update_file(
                    file_content.path,
                    f"Update {file_content.name}: {llm_response['reasoning']}",
                    modified_content,
                    file_content.sha
                )
                
                results.append({
                    "file": file_content.path,
                    "success": True,
                    "changes": llm_response,
                    "reasoning": llm_response["reasoning"]
                })
                
            except Exception as e:
                results.append({
                    "file": file_content.path,
                    "error": f"GitHub update failed: {str(e)}"
                })
        
        return {"results": results, "total_files": len(matching_files)}

# Usage example
def main():
    modifier = GitHubYAMLModifier(
        github_token="your_github_token",
        openai_api_key="your_openai_key", 
        repo_name="username/repository"
    )
    
    # Define criteria for finding files
    criteria = {
        "filename_pattern": ".yml",  # or specific pattern like "config.yml"
        "required_directories": ["configs", "environments"]  # directories that must exist in path
    }
    
    # Chat request
    user_message = "Add a new property called 'timeout' with value 30 to all configuration files"
    
    result = modifier.process_chat_request(user_message, criteria)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()