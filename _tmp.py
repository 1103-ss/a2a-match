import subprocess, os
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\a2a-match')
subprocess.run(['git', 'add', '-A'], check=True)
r = subprocess.run(['git', 'commit', '-m', 'v2.1.0: match inline messaging - @mention to chat in Claw'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout or r.stderr or 'committed')
