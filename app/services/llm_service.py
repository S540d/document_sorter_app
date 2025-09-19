"""
LLM (Language Model) Service für die Dokumentenklassifizierung
"""
import requests
from typing import List, Optional
from ..config.config_manager import ConfigManager

class LLMService:
    """Service für die Interaktion mit dem Language Model"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.llm_url = self.config.get('LM_STUDIO_URL')
    
    def classify_document(self, text: str, categories: List[str]) -> str:
        """Klassifiziert ein Dokument basierend auf seinem Inhalt"""
        prompt = f"""Du bist ein Experte für Dokumentenklassifizierung.
Analysiere den folgenden Text und wähle die passendste Kategorie:

Verfügbare Kategorien: {', '.join(categories)}

Dokumententext:
{text[:2000]}

Antworte nur mit der Kategorie, nichts anderes. Falls unsicher, wähle 'Sonstiges'."""
        
        try:
            response = self._call_llm(prompt)
            if response:
                category = response.strip()
                return category if category in categories else 'Sonstiges'
        except Exception as e:
            print(f"Error in document classification: {e}")
        
        return 'Sonstiges'
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Sendet eine Anfrage an das Language Model"""
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": "deepseek-r1",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"LM Studio Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error calling LM Studio: {e}")
            return None