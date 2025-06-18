#!/usr/bin/env python3
"""
GitHub APK Builder Tool
Automates the process of pushing Android projects to GitHub and building APKs via GitHub Actions
"""

import os
import json
import time
import subprocess
import requests
from pathlib import Path
import zipfile
import tempfile
import sys
from datetime import datetime

class GitHubAPKBuilder:
    def __init__(self):
        self.config_file = "github_builder_config.json"
        self.config = self.load_config()
        self.headers = {}
        
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        self.config = config
        
    def setup_credentials(self):
        """Setup GitHub credentials and user details"""
        print("=== GitHub APK Builder Setup ===")
        print()
        print("🔑 Your GitHub Personal Access Token needs these permissions:")
        print("   - repo (Full control of private repositories)")
        print("   - workflow (Update GitHub Action workflows)")
        print("   - read:user (Read user profile data)")
        print()
        print("To create a token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Select the scopes mentioned above")
        print("4. Generate and copy the token")
        print()
        
        if not self.config.get('github_token'):
            token = input("Enter your GitHub Personal Access Token: ").strip()
            if not token:
                print("❌ GitHub token is required!")
                return False
            self.config['github_token'] = token
        
        if not self.config.get('github_username'):
            username = input("Enter your GitHub username: ").strip()
            if not username:
                print("❌ GitHub username is required!")
                return False
            self.config['github_username'] = username
            
        if not self.config.get('email'):
            email = input("Enter your email address: ").strip()
            if not email:
                print("❌ Email is required!")
                return False
            self.config['email'] = email
            
        self.save_config(self.config)
        self.headers = {
            'Authorization': f'token {self.config["github_token"]}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Test the token and check permissions
        response = requests.get('https://api.github.com/user', headers=self.headers)
        if response.status_code != 200:
            print("❌ Invalid GitHub token!")
            return False
            
        # Check token scopes
        scopes = response.headers.get('X-OAuth-Scopes', '').split(', ')
        required_scopes = ['repo', 'workflow']
        missing_scopes = [scope for scope in required_scopes if scope not in scopes and 'repo' not in ' '.join(scopes)]
        
        if missing_scopes:
            print(f"⚠️  Warning: Your token might be missing these scopes: {', '.join(missing_scopes)}")
            print("   This might cause issues with creating repositories or workflows.")
            
        print("✅ GitHub credentials verified!")
        return True
        
    def check_git_repo(self):
        """Check if current directory is a git repository"""
        return os.path.exists('.git')
        
    def init_git_repo(self):
        """Initialize git repository"""
        print("📂 Initializing git repository...")
        try:
            subprocess.run(['git', 'init'], check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', self.config['github_username']], check=True)
            subprocess.run(['git', 'config', 'user.email', self.config['email']], check=True)
            print("✅ Git repository initialized!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to initialize git repo: {e}")
            return False
            
    def create_github_repo(self, repo_name):
        """Create a new GitHub repository"""
        print(f"🔨 Creating GitHub repository: {repo_name}")
        
        data = {
            'name': repo_name,
            'description': f'Android APK build for {repo_name}',
            'private': False,
            'auto_init': False
        }
        
        response = requests.post('https://api.github.com/user/repos', 
                               headers=self.headers, json=data)
        
        if response.status_code == 201:
            print("✅ GitHub repository created!")
            return True
        elif response.status_code == 422:
            error_data = response.json()
            if 'already exists' in str(error_data):
                print("⚠️  Repository already exists, continuing...")
                return True
            else:
                print(f"❌ Repository creation failed: {error_data}")
                return False
        elif response.status_code == 403:
            print("❌ Permission denied! Your GitHub token needs 'repo' scope.")
            print("   Please create a new token with proper permissions:")
            print("   1. Go to https://github.com/settings/tokens")
            print("   2. Click 'Generate new token (classic)'")
            print("   3. Select 'repo' scope (Full control of private repositories)")
            print("   4. Generate and copy the token")
            print("   5. Run the script again with --setup to update your token")
            return False
        else:
            print(f"❌ Failed to create repository: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                print(f"   Error response: {response.text}")
            return False
            
    def create_workflow_file(self):
        """Create GitHub Actions workflow for Android build"""
        workflow_dir = '.github/workflows'
        os.makedirs(workflow_dir, exist_ok=True)
        
        workflow_content = """name: Android Build Dynamo Calc

on:
  push:
    branches:
      - main
      - develop
  pull_request:
    branches:
      - main
      - develop

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17' # Ensure this matches your project's compileOptions.targetCompatibility
          distribution: 'temurin'
          cache: 'gradle'

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Build Debug APK
        run: ./gradlew assembleDebug

      - name: Upload Debug APK
        uses: actions/upload-artifact@v4
        with:
          name: DynamoCalc-debug-apk
          path: app/build/outputs/apk/debug/app-debug.apk

      - name: Run Unit Tests
        run: ./gradlew testDebugUnitTest

      - name: Upload Unit Test Results
        uses: actions/upload-artifact@v4
        with:
          name: unit-test-results
          path: app/build/reports/tests/testDebugUnitTest/

      # Optional: Add steps for release build, signing, or publishing if needed
      # - name: Build Release APK (requires signing setup)
      #   run: ./gradlew assembleRelease
      #   env:
      #     KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
      #     KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
      #     KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      #     # Add other necessary signing environment variables here

      # - name: Upload Release APK
      #   if: success() # Only upload if build is successful
      #   uses: actions/upload-artifact@v4
      #   with:
      #     name: DynamoCalc-release-apk
      #     path: app/build/outputs/apk/release/app-release.apk
"""
        
        workflow_file = os.path.join(workflow_dir, 'build.yml')
        with open(workflow_file, 'w') as f:
            f.write(workflow_content)
            
        # Create .gitignore to exclude sensitive files
        gitignore_content = """# GitHub APK Builder - Exclude sensitive config
github_builder_config.json

# Android Studio
*.iml
.gradle
/local.properties
/.idea/caches
/.idea/libraries
/.idea/modules.xml
/.idea/workspace.xml
/.idea/navEditor.xml
/.idea/assetWizardSettings.xml
.DS_Store
/build
/captures
.externalNativeBuild
.cxx
local.properties

# APK files
*.apk
*.aab

# Keystore files
*.jks
*.keystore
"""
        
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
            
        print("✅ GitHub Actions workflow created!")
        print("✅ .gitignore created to protect sensitive files!")
        
    def cleanup_git_history(self):
        """Completely clean git history to remove sensitive data"""
        print("🧹 Cleaning git history to remove sensitive data...")
        
        try:
            # Remove the config file completely
            if os.path.exists('github_builder_config.json'):
                subprocess.run(['git', 'rm', '--cached', 'github_builder_config.json'], 
                              capture_output=True)
            
            # Reset to initial state
            result = subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], 
                                  capture_output=True, text=True)
            
            # If that doesn't work, start completely fresh
            if result.returncode != 0:
                print("🔄 Starting with a clean git history...")
                # Remove .git directory and start fresh
                import shutil
                if os.path.exists('.git'):
                    shutil.rmtree('.git')
                
                # Re-initialize git
                subprocess.run(['git', 'init'], capture_output=True)
                subprocess.run(['git', 'config', 'user.name', self.config['github_username']], capture_output=True)
                subprocess.run(['git', 'config', 'user.email', self.config['email']], capture_output=True)
                
            print("✅ Git history cleaned!")
            return True
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
            return False
            
    def commit_and_push(self, repo_name):
        """Commit files and push to GitHub"""
        print("📤 Committing and pushing to GitHub...")
        
        try:
            # Add all files (gitignore will exclude sensitive ones)
            result = subprocess.run(['git', 'add', '.'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Git add failed: {result.stderr}")
                return False
            
            # Check if there are changes to commit
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            if not result.stdout.strip():
                print("ℹ️  No changes to commit")
                return True
            
            # Commit
            commit_msg = f"Initial commit - APK build setup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Git commit failed: {result.stderr}")
                return False
            
            # Set up remote URL with token authentication
            remote_url = f"https://{self.config['github_token']}@github.com/{self.config['github_username']}/{repo_name}.git"
            
            # Remove existing origin if exists
            subprocess.run(['git', 'remote', 'remove', 'origin'], capture_output=True)
            
            # Add remote with authentication
            result = subprocess.run(['git', 'remote', 'add', 'origin', remote_url], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to add remote: {result.stderr}")
                return False
            
            # Ensure we're on main branch
            subprocess.run(['git', 'branch', '-M', 'main'], capture_output=True)
            
            # Push to main branch with --force
            print("🔄 Pushing to GitHub... (this may take a moment)")
            # ADDED --force HERE
            result = subprocess.run(['git', 'push', '-u', 'origin', 'main', '--force'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Git push failed:")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                
                # Try to give helpful suggestions
                if "remote rejected" in result.stderr.lower():
                    print("💡 Suggestion: The remote repository might have protection rules.")
                elif "authentication failed" in result.stderr.lower():
                    print("💡 Suggestion: Check if your GitHub token has 'repo' permissions.")
                elif "repository not found" in result.stderr.lower():
                    print("💡 Suggestion: Make sure the repository was created successfully.")
                
                return False
            
            print("✅ Code pushed to GitHub!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to push to GitHub: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
            
    def get_workflow_runs(self, repo_name):
        """Get workflow runs for the repository"""
        url = f"https://api.github.com/repos/{self.config['github_username']}/{repo_name}/actions/runs"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()['workflow_runs']
        return []
        
    def get_workflow_logs(self, repo_name, run_id):
        """Download and display workflow logs"""
        url = f"https://api.github.com/repos/{self.config['github_username']}/{repo_name}/actions/runs/{run_id}/logs"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            # Save logs to temporary file and extract
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            try:
                with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                    # Extract and display logs
                    for file_name in zip_file.namelist():
                        if file_name.endswith('.txt'):
                            with zip_file.open(file_name) as log_file:
                                content = log_file.read().decode('utf-8')
                                print(f"\n=== {file_name} ===")
                                print(content)
            finally:
                os.unlink(temp_file_path)
        else:
            print("❌ Failed to download logs")
            
    def download_apk(self, repo_name, run_id):
        """Download the built APK"""
        # Get artifacts
        url = f"https://api.github.com/repos/{self.config['github_username']}/{repo_name}/actions/runs/{run_id}/artifacts"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print("❌ Failed to get artifacts")
            return False
            
        artifacts = response.json()['artifacts']
        apk_artifact = None
        
        for artifact in artifacts:
            if artifact['name'] == 'app-debug':
                apk_artifact = artifact
                break
                
        if not apk_artifact:
            print("❌ APK artifact not found")
            return False
            
        # Download artifact
        download_url = apk_artifact['archive_download_url']
        response = requests.get(download_url, headers=self.headers)
        
        if response.status_code == 200:
            # Save and extract APK
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            try:
                with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                    zip_file.extractall('.')
                    print("✅ APK downloaded successfully!")
                    
                    # Find the APK file
                    for root, dirs, files in os.walk('.'):
                        for file in files:
                            if file.endswith('.apk'):
                                apk_path = os.path.join(root, file)
                                print(f"📱 APK ready for installation: {apk_path}")
                                return True
            finally:
                os.unlink(temp_file_path)
        else:
            print("❌ Failed to download APK")
            
        return False
        
    def monitor_build(self, repo_name):
        """Monitor the build process and show logs"""
        print("🔄 Monitoring build process...")
        
        max_attempts = 60  # 10 minutes timeout
        attempt = 0
        
        while attempt < max_attempts:
            runs = self.get_workflow_runs(repo_name)
            
            if runs:
                latest_run = runs[0]
                status = latest_run['status']
                conclusion = latest_run['conclusion']
                run_id = latest_run['id']
                
                print(f"📊 Build Status: {status} | Conclusion: {conclusion}")
                
                if status == 'completed':
                    if conclusion == 'success':
                        print("✅ Build completed successfully!")
                        self.download_apk(repo_name, run_id)
                        return True
                    else:
                        print("❌ Build failed!")
                        print("\n=== Build Logs ===")
                        self.get_workflow_logs(repo_name, run_id)
                        return False
                        
            time.sleep(10)  # Wait 10 seconds before checking again
            attempt += 1
            
        print("⏰ Build timeout - please check GitHub Actions manually")
        return False
        
    def run(self):
        """Main execution flow"""
        print("🚀 GitHub APK Builder Started")
        
        # Setup credentials
        if not self.setup_credentials():
            return
            
        # Get current directory name as repo name
        current_dir = os.path.basename(os.getcwd())
        repo_name = input(f"Repository name [{current_dir}]: ").strip() or current_dir
        
        # Check if it's an Android project
        if not (os.path.exists('app/build.gradle') or os.path.exists('build.gradle')):
            print("⚠️  This doesn't appear to be an Android project directory")
            if input("Continue anyway? (y/N): ").lower() != 'y':
                return
                
        # Initialize git if needed
        if not self.check_git_repo():
            if not self.init_git_repo():
                return
                
        # Create GitHub repository
        if not self.create_github_repo(repo_name):
            return
            
        # Create workflow file
        self.create_workflow_file()
        
        # Commit and push
        if not self.commit_and_push(repo_name):
            return
            
        # Monitor build
        if self.monitor_build(repo_name):
            print("🎉 APK build process completed successfully!")
        else:
            print("💡 You can fix the issues and run the script again to retry")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        # Setup mode - just configure credentials
        builder = GitHubAPKBuilder()
        builder.setup_credentials()
    elif len(sys.argv) > 1 and sys.argv[1] == '--reset':
        # Reset configuration
        config_file = "github_builder_config.json"
        if os.path.exists(config_file):
            os.remove(config_file)
            print("🗑️  Configuration reset! Run with --setup to reconfigure.")
        else:
            print("ℹ️  No configuration found to reset.")
    elif len(sys.argv) > 1 and sys.argv[1] == '--clean':
        # Clean git history completely
        print("🧹 Cleaning git repository completely...")
        import shutil
        if os.path.exists('.git'):
            shutil.rmtree('.git')
            print("✅ Git history removed. Run the script again to start fresh.")
        else:
            print("ℹ️  No git repository found to clean.")
    else:
        # Full run mode
        builder = GitHubAPKBuilder()
        builder.run()

if __name__ == "__main__":
    main()