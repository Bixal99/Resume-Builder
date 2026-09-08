import os
import re

templates_dir = r'd:\My_products\Automated_CV_Generator\app\templates\resume_templates'

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file == 'template.html':
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = re.sub(
                r'<p class="entry-description">\s*\{\{\s*([\w\.]+)\s*\}\}\s*</p>',
                r'<div class="entry-description">{{ \1 | parse_bullets }}</div>',
                content
            )
            
            new_content = re.sub(
                r'<p class="summary-text">\s*\{\{\s*([\w\.]+)\s*\}\}\s*</p>',
                r'<div class="summary-text">{{ \1 | parse_bullets }}</div>',
                new_content
            )
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Updated {filepath}')
            else:
                print(f'No changes for {filepath}')
