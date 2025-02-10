import os
import requests

class Updater:
    def __init__(self):
        self.repo_owner = "0x8fv"
        self.repo_name = "Twitch-Channel-Points-Miner-v2"
        self.branch = "master"
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.raw_base_url = f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/{self.branch}"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    def get_remote_files(self):
        try:
            response = requests.get(f"{self.base_url}/branches/{self.branch}")
            response.raise_for_status()
            latest_commit_sha = response.json()['commit']['sha']

            tree_url = f"{self.base_url}/git/trees/{latest_commit_sha}?recursive=1"
            response = requests.get(tree_url)
            response.raise_for_status()
            return [file['path'] for file in response.json()['tree'] if file['type'] == 'blob']
        except requests.exceptions.RequestException as e:
            print(f"Error fetching remote files: {e}")
            return []

    def update(self):
        print("Checking for updates...")
        remote_files = self.get_remote_files()
        if not remote_files:
            print("No remote files fetched. Update aborted.")
            return False

        updated_files = []
        for file_path in remote_files:
            remote_url = f"{self.raw_base_url}/{file_path}"
            try:
                response = requests.get(remote_url)
                response.raise_for_status()
            except requests.exceptions.RequestException:
                print(f"Failed to download: {file_path}")
                continue

            remote_content = response.content
            local_path = os.path.join(self.script_dir, file_path)

            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    local_content = f.read()
                if local_content == remote_content:
                    continue

            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            try:
                with open(local_path, 'wb') as f:
                    f.write(remote_content)
                updated_files.append(file_path)
            except IOError as e:
                print(f"Error writing {file_path}: {e}")

        if updated_files:
            print(f"Updated {len(updated_files)} files:")
            for file in updated_files:
                print(f" - {file}")
            print("\nUpdate complete. Please restart the application.")
            return True
        else:
            print("No updates required.")
            return