#!/usr/bin/env python3
import re
import os

def remove_comments_and_emojis(content, file_type='python'):
    """Remove comments and emojis from code while preserving functionality"""
    
    if file_type == 'python':
        lines = content.split('\n')
        cleaned_lines = []
        in_multiline = False
        multiline_char = None
        
        for line in lines:
            stripped = line.lstrip()
            
            if in_multiline:
                if multiline_char in line:
                    in_multiline = False
                continue
            
            if stripped.startswith('"""') or stripped.startswith("'''"):
                multiline_char = '"""' if '"""' in line else "'''"
                if line.count(multiline_char) == 2:
                    continue
                else:
                    in_multiline = True
                    continue
            
            if '#' in line:
                code_part = line.split('#')[0]
                if code_part.strip():
                    line = code_part
                else:
                    continue
            
            line = remove_emojis(line)
            
            if line.strip():
                cleaned_lines.append(line)
            elif not line.strip() and cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)
    
    elif file_type == 'javascript':
        lines = content.split('\n')
        cleaned_lines = []
        in_multiline = False
        
        for line in lines:
            if '/*' in line and '*/' in line:
                comment_start = line.find('/*')
                comment_end = line.find('*/')
                if comment_start < comment_end:
                    line = line[:comment_start] + line[comment_end+2:]
            elif '/*' in line:
                in_multiline = True
                comment_start = line.find('/*')
                line = line[:comment_start]
            elif in_multiline and '*/' in line:
                in_multiline = False
                comment_end = line.find('*/')
                line = line[comment_end+2:]
            elif in_multiline:
                continue
            
            if '//' in line:
                comment_start = line.find('//')
                line = line[:comment_start]
            
            line = remove_emojis(line)
            
            if line.strip():
                cleaned_lines.append(line)
            elif not line.strip() and cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)
    
    elif file_type == 'html':
        content = remove_emojis(content)
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if '<!--' in line and '-->' in line:
                comment_start = line.find('<!--')
                comment_end = line.find('-->')
                line = line[:comment_start] + line[comment_end+3:]
            
            if line.strip():
                cleaned_lines.append(line)
            elif not line.strip() and cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)
    
    return content

def remove_emojis(text):
    """Remove emoji characters from text"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def clean_file(filepath, file_type):
    """Clean a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        cleaned_content = remove_comments_and_emojis(content, file_type)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        return True, f"Cleaned {filepath}"
    except Exception as e:
        return False, f"Error cleaning {filepath}: {str(e)}"

def main():
    files_to_clean = [
        ('/home/ahad/Desktop/help/enhanced_api.py', 'python'),
        ('/home/ahad/Desktop/help/cms/ids_manager.py', 'python'),
        ('/home/ahad/Desktop/help/cms/deployment_manager.py', 'python'),
        ('/home/ahad/Desktop/help/cms/health_monitor.py', 'python'),
        ('/home/ahad/Desktop/help/static/js/dashboard.js', 'javascript'),
        ('/home/ahad/Desktop/help/templates/dashboard.html', 'html'),
    ]
    
    print("=" * 70)
    print("CODE CLEANUP UTILITY")
    print("Removing comments and emojis from all files")
    print("=" * 70)
    print()
    
    success_count = 0
    for filepath, ftype in files_to_clean:
        if os.path.exists(filepath):
            success, message = clean_file(filepath, ftype)
            status = "[OK]" if success else "[ERROR]"
            print(f"{status} {message}")
            if success:
                success_count += 1
        else:
            print(f"[SKIP] File not found: {filepath}")
    
    print()
    print("=" * 70)
    print(f"Cleanup complete: {success_count}/{len([f for f in files_to_clean if os.path.exists(f[0])])} files processed")
    print("=" * 70)

if __name__ == '__main__':
    main()
