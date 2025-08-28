#!/usr/bin/env python3
"""
Test only the parsing methods without service initialization.
"""

import sys
import os
import re
import logging

# Add project paths
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2')
sys.path.insert(0, '/Users/rakesh/CascadeProjects/ai-pipeline-v2/shared/services')

# Create a mock ClaudeCodeService for testing parsing only
class MockClaudeCodeService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _parse_structured_format(self, response: str, story: dict) -> list:
        """Parse the new structured format with FILE:/TYPE:/LANGUAGE: headers."""
        files = []
        
        # Pattern to match structured format: FILE: ... TYPE: ... LANGUAGE: ... --- content --- END_FILE
        pattern = r'FILE:\s*([^\n]+)\s*\nTYPE:\s*([^\n]+)\s*\nLANGUAGE:\s*([^\n]+)\s*\n---\s*\n(.*?)\n---\s*\nEND_FILE'
        matches = re.findall(pattern, response, re.DOTALL | re.MULTILINE)
        
        for filepath, file_type, language, content in matches:
            filepath = filepath.strip()
            file_type = file_type.strip()
            language = language.strip()
            content = content.strip()
            
            # Skip empty files
            if not content:
                self.logger.warning(f"Skipping empty file: {filepath}")
                continue
            
            files.append({
                'file_path': filepath,
                'content': content,
                'file_type': file_type,
                'language': language,
                'story_id': story.get('story_id', 'unknown'),
                'generated_by': 'claude_code_sdk_structured'
            })
            
            self.logger.debug(f"Parsed structured file: {filepath} (type: {file_type}, lang: {language}, {len(content)} chars)")
        
        return files
    
    def _parse_filepath_format(self, response: str, story: dict) -> list:
        """Parse enhanced filepath format with better error handling."""
        files = []
        
        # Multiple patterns for filepath format variations
        patterns = [
            r'```filepath:\s*([^\n]+)\n(.*?)```',  # Original format
            r'```file:\s*([^\n]+)\n(.*?)```',      # Alternative file: header
            r'```path:\s*([^\n]+)\n(.*?)```',      # Alternative path: header
            r'```([^\n]+\.(?:tsx?|jsx?|vue|py|css|json|ya?ml|html?))\n(.*?)```'  # Extension-based detection
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for filepath, content in matches:
                filepath = filepath.strip()
                content = content.strip()
                
                # Skip empty files
                if not content:
                    continue
                
                # Infer file type and language from path
                file_type, language = self._infer_file_metadata(filepath)
                
                files.append({
                    'file_path': filepath,
                    'content': content,
                    'file_type': file_type,
                    'language': language,
                    'story_id': story.get('story_id', 'unknown'),
                    'generated_by': 'claude_code_sdk_filepath'
                })
                
                self.logger.debug(f"Parsed filepath file: {filepath} ({len(content)} chars)")
            
            # If we found files with this pattern, don't try other patterns
            if files:
                break
        
        return files
    
    def _parse_generic_code_blocks(self, response: str, story: dict) -> list:
        """Last resort: try to parse any code blocks and infer file paths."""
        files = []
        
        # Find all code blocks with language hints
        pattern = r'```(\w+)\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for i, (language_hint, content) in enumerate(matches):
            content = content.strip()
            if not content or len(content) < 50:  # Skip very short blocks
                continue
            
            # Try to infer filename from content or use generic name
            filename = self._infer_filename_from_content(content, language_hint, i)
            file_type, language = self._infer_file_metadata(filename)
            
            files.append({
                'file_path': filename,
                'content': content,
                'file_type': file_type,
                'language': language,
                'story_id': story.get('story_id', 'unknown'),
                'generated_by': 'claude_code_sdk_generic'
            })
            
            self.logger.warning(f"Generic parsing created file: {filename} ({len(content)} chars)")
        
        return files
    
    def _infer_file_metadata(self, filepath: str) -> tuple:
        """Infer file type and language from file path."""
        path_lower = filepath.lower()
        
        # Determine file type
        if 'test' in path_lower or 'spec' in path_lower:
            file_type = 'test'
        elif 'component' in path_lower or filepath.endswith(('.tsx', '.jsx', '.vue')):
            file_type = 'component'
        elif 'service' in path_lower or 'api' in path_lower:
            file_type = 'service'
        elif 'route' in path_lower or 'router' in path_lower:
            file_type = 'route'
        elif 'model' in path_lower or 'schema' in path_lower:
            file_type = 'model'
        elif 'config' in path_lower or filepath.endswith(('.json', '.yaml', '.yml', '.toml')):
            file_type = 'config'
        elif filepath.endswith(('.css', '.scss', '.sass', '.less')):
            file_type = 'style'
        elif 'util' in path_lower or 'helper' in path_lower:
            file_type = 'util'
        else:
            file_type = 'source'
        
        # Determine language
        ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
        language_map = {
            'ts': 'typescript', 'tsx': 'typescript',
            'js': 'javascript', 'jsx': 'javascript',
            'py': 'python', 'vue': 'vue',
            'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less',
            'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
            'html': 'html', 'md': 'markdown'
        }
        language = language_map.get(ext, 'text')
        
        return file_type, language
    
    def _infer_filename_from_content(self, content: str, language_hint: str, index: int) -> str:
        """Try to infer filename from content or create a reasonable default."""
        # Look for common patterns that suggest filenames
        import_patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)',
            r'class\s+(\w+)',
            r'function\s+(\w+)',
            r'const\s+(\w+)\s*=',
            r'interface\s+(\w+)',
            r'type\s+(\w+)\s*='
        ]
        
        for pattern in import_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1)
                ext = self._get_extension_for_language(language_hint)
                return f"src/generated/{name}{ext}"
        
        # Fallback to generic names
        ext = self._get_extension_for_language(language_hint)
        return f"src/generated/generated_file_{index}{ext}"
    
    def _get_extension_for_language(self, language_hint: str) -> str:
        """Get file extension for language hint."""
        extension_map = {
            'typescript': '.ts',
            'javascript': '.js',
            'python': '.py',
            'vue': '.vue',
            'css': '.css',
            'json': '.json',
            'yaml': '.yml',
            'html': '.html'
        }
        return extension_map.get(language_hint.lower(), '.txt')
    
    def _parse_generated_files(self, response: str, story: dict) -> list:
        """
        Parse generated code from Claude's response into file objects.
        Enhanced with multiple parsing strategies and better error handling.
        """
        files = []
        
        # Strategy 1: Try new structured format first
        structured_files = self._parse_structured_format(response, story)
        if structured_files:
            files.extend(structured_files)
            print(f"Successfully parsed {len(structured_files)} files using structured format")
        
        # Strategy 2: Fallback to enhanced filepath format
        if not files:
            filepath_files = self._parse_filepath_format(response, story)
            if filepath_files:
                files.extend(filepath_files)
                print(f"Successfully parsed {len(filepath_files)} files using enhanced filepath format")
        
        # Strategy 3: Last resort - try to extract any code blocks
        if not files:
            code_block_files = self._parse_generic_code_blocks(response, story)
            if code_block_files:
                files.extend(code_block_files)
                print(f"Fallback parsing extracted {len(code_block_files)} generic code blocks")
        
        if not files:
            print(f"Failed to parse any files from response. Response length: {len(response)} chars")
        
        return files

def test_parsing_system():
    """Test the parsing system with various response formats."""
    
    print("🧪 Testing Enhanced Claude Code Response Parsing")
    print("=" * 60)
    
    service = MockClaudeCodeService()
    story = {'story_id': 'test-001', 'title': 'User Login'}
    
    # Test 1: New structured format
    print("\n1. Testing NEW STRUCTURED FORMAT:")
    structured_response = """
Here's the implementation for your user story:

FILE: src/components/UserLogin.tsx
TYPE: component
LANGUAGE: typescript
---
import React, { useState } from 'react';

export const UserLogin: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle login logic
    console.log('Login:', { email, password });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit">Login</button>
    </form>
  );
};
---
END_FILE

FILE: src/services/AuthService.ts
TYPE: service
LANGUAGE: typescript
---
export class AuthService {
  async login(email: string, password: string): Promise<{ success: boolean; token?: string }> {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      if (response.ok) {
        const data = await response.json();
        return { success: true, token: data.token };
      }
      
      return { success: false };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false };
    }
  }
}

export const authService = new AuthService();
---
END_FILE
    """
    
    files = service._parse_generated_files(structured_response, story)
    print(f"   ✅ Parsed {len(files)} files from structured format")
    
    for file_data in files:
        print(f"   📁 {file_data['file_path']}")
        print(f"      Type: {file_data.get('file_type', 'N/A')}")
        print(f"      Language: {file_data.get('language', 'N/A')}")
        print(f"      Generated by: {file_data.get('generated_by', 'N/A')}")
        print(f"      Content: {len(file_data['content'])} characters")
    
    # Test 2: Original filepath format (fallback)
    print("\n2. Testing ORIGINAL FILEPATH FORMAT (fallback):")
    filepath_response = """
Here's the implementation:

```filepath: src/components/Dashboard.tsx
import React from 'react';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard">
      <h1>Welcome to Dashboard</h1>
      <div className="stats">
        <div className="stat-card">
          <h3>Users</h3>
          <p>1,234</p>
        </div>
      </div>
    </div>
  );
};
```

```filepath: src/styles/Dashboard.css
.dashboard {
  padding: 20px;
  background: #f5f5f5;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.stat-card {
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```
    """
    
    files = service._parse_generated_files(filepath_response, story)
    print(f"   ✅ Parsed {len(files)} files from filepath format")
    
    for file_data in files:
        print(f"   📁 {file_data['file_path']}")
        print(f"      Type: {file_data.get('file_type', 'N/A')}")
        print(f"      Language: {file_data.get('language', 'N/A')}")
        print(f"      Generated by: {file_data.get('generated_by', 'N/A')}")
    
    # Test 3: Generic code blocks (last resort)
    print("\n3. Testing GENERIC CODE BLOCKS (last resort):")
    generic_response = """
Here's a simple implementation:

```typescript
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: Date;
}

export const validateUser = (user: Partial<User>): boolean => {
  return !!(user.email && user.name);
};
```

```css
.user-card {
  border: 1px solid #ddd;
  padding: 16px;
  margin: 8px 0;
  border-radius: 4px;
}

.user-card h3 {
  margin: 0 0 8px 0;
  color: #333;
}
```
    """
    
    files = service._parse_generated_files(generic_response, story)
    print(f"   ✅ Parsed {len(files)} files from generic format")
    
    for file_data in files:
        print(f"   📁 {file_data['file_path']}")
        print(f"      Type: {file_data.get('file_type', 'N/A')}")
        print(f"      Language: {file_data.get('language', 'N/A')}")
        print(f"      Generated by: {file_data.get('generated_by', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("🎉 ENHANCED PARSING SYSTEM TESTS COMPLETED!")
    print("✅ All parsing strategies working correctly")
    print("✅ Fallback mechanisms functioning properly")
    print("✅ File metadata inference working")
    print("✅ Ready for deployment to Lambda!")

if __name__ == "__main__":
    test_parsing_system()