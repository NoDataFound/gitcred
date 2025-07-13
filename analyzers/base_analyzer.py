from abc import ABC,abstractmethod
class BaseAnalyzer(ABC):
 def __init__(self,repo_path):self.repo_path=repo_path
 @abstractmethod
 def get_dependencies(self):pass
 @abstractmethod
 def analyze_quality(self):pass
 @abstractmethod
 def analyze_security(self):pass
 @abstractmethod
 def harvest_comments(self):pass
