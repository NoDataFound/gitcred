import os,subprocess,json
from .base_analyzer import BaseAnalyzer
class PythonAnalyzer(BaseAnalyzer):
 def get_dependencies(self):
  deps,p=[],os.path.join(self.repo_path,'requirements.txt')
  if os.path.exists(p):
   try:
    with open(p,'r',errors='ignore') as f:deps=[l.split('==')[0].strip().lower() for l in f if l.strip() and not l.startswith('#')]
   except:pass
  return deps
 def analyze_quality(self):
  v,f=0,0
  for r,_,fs in os.walk(self.repo_path):
   for fl in fs:
    if fl.endswith((".py", ".ipynb")):
     f+=1
     if fl.endswith(".py"): # Only lint pure python files
      try:
       res=subprocess.run(['flake8',os.path.join(r,fl)],capture_output=True,text=True,check=False)
       if res.stdout:v+=len(res.stdout.strip().split('\n'))
      except:pass
  return {"violations":v,"files_analyzed":f}
 def analyze_security(self):
  try:
   res=subprocess.run(['bandit','-r',self.repo_path,'-f','json'],capture_output=True,text=True,check=False)
   return json.loads(res.stdout).get('results',[])
  except:return []
 def harvest_comments(self):
  cs=[]
  for r,_,fs in os.walk(self.repo_path):
   for fl in fs:
    if fl.endswith(".py"): # Currently only parsing .py files for comments
     fp=os.path.join(r,fl)
     try:
      with open(fp,'r',encoding='utf-8',errors='ignore') as f:
       for i,l in enumerate(f,1):
        if'#'in l:
         ct=l.split('#',1)[1].strip()
         if ct:cs.append({"file_name":os.path.relpath(fp,self.repo_path),"line":i,"comment":ct})
     except:pass
  return cs
