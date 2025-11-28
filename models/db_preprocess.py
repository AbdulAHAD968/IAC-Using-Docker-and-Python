import pandas as pd
import re

def parse_db_log(line):
    """Extracts the SQL query from the MySQL general log"""
    # MySQL Log Format Example: 
    # 2025-11-19T10:00:00.123456Z   3 Query   SELECT * FROM users
    
    # 1. Clean whitespace
    line = line.strip()
    
    # 2. Look for common command types followed by a tab or space
    # We look for 'Query', 'Execute', or just grab the end of the line
    match = re.search(r'\s+(Query|Execute)\s+(.*)', line)
    if match:
        return match.group(2).strip()
        
    # 3. Fallback: If it doesn't match standard format, return the line 
    # (It might be a raw query if the log format is custom)
    return line

def extract_sql_features(df):
    """Converts SQL Text -> Numbers (Matches Colab Training Logic)"""
    # Work on a copy to avoid SettingWithCopyWarning
    data = df.copy()
    
    # Ensure string
    data['query'] = data['query'].astype(str)
    
    # 1. Length
    data['length'] = data['query'].apply(len)
    
    # 2. Keyword Count
    keywords = ["SELECT", "UNION", "INSERT", "UPDATE", "DELETE", "DROP", "FROM", "WHERE"]
    data['keyword_count'] = data['query'].apply(lambda x: sum(x.upper().count(k) for k in keywords))
    
    # 3. Special Char Count
    data['special_chars'] = data['query'].apply(lambda x: sum(x.count(c) for c in ["'", '"', "-", "#", ";", "=", "(", ")", "*"]))
    
    # 4. Logic Spikes
    data['logic_count'] = data['query'].apply(lambda x: sum(x.upper().count(k) for k in [" OR ", " AND ", "1=1", "1=0"]))
    
    # 5. Comment Detection
    data['has_comment'] = data['query'].apply(lambda x: 1 if "--" in x or "#" in x else 0)

    return data[['length', 'keyword_count', 'special_chars', 'logic_count', 'has_comment']]