"""
File Renaming Service
Handles intelligent file renaming based on category and extracted dates
"""

import re
from datetime import datetime, date
from typing import List, Optional, Tuple
from pathlib import Path


class FileRenamingService:
    """Service for intelligent file renaming"""

    def __init__(self):
        # German date patterns (most common first)
        self.date_patterns = [
            # DD.MM.YYYY or DD/MM/YYYY
            r'(\d{1,2})[./](\d{1,2})[./](\d{4})',
            # YYYY-MM-DD (ISO format)
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # DD.MM.YY or DD/MM/YY
            r'(\d{1,2})[./](\d{1,2})[./](\d{2})',
            # Month names in German
            r'(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})',
            # Month abbreviations
            r'(\d{1,2})\.\s*(Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\s*(\d{4})',
        ]

        # Month name mapping
        self.month_names = {
            'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6,
            'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12,
            'jan': 1, 'feb': 2, 'mär': 3, 'apr': 4, 'mai': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dez': 12
        }

    def extract_dates_from_text(self, text: str) -> List[date]:
        """Extract all valid dates from text content"""
        found_dates = []

        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) == 3:
                        if pattern == self.date_patterns[0]:  # DD.MM.YYYY
                            day, month, year = map(int, match.groups())
                        elif pattern == self.date_patterns[1]:  # YYYY-MM-DD
                            year, month, day = map(int, match.groups())
                        elif pattern == self.date_patterns[2]:  # DD.MM.YY
                            day, month, year_short = map(int, match.groups())
                            year = 2000 + year_short if year_short < 50 else 1900 + year_short
                        elif 'januar' in pattern.lower() or 'jan' in pattern.lower():
                            day = int(match.groups()[0])
                            month_name = match.groups()[1].lower()
                            year = int(match.groups()[2])
                            month = self.month_names.get(month_name, 0)
                            if month == 0:
                                continue

                        # Validate date
                        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                            parsed_date = date(year, month, day)
                            if parsed_date not in found_dates:
                                found_dates.append(parsed_date)
                except (ValueError, TypeError):
                    continue

        return sorted(found_dates)

    def get_most_recent_past_date(self, dates: List[date]) -> Optional[date]:
        """Get the most recent date that is in the past"""
        today = date.today()
        past_dates = [d for d in dates if d <= today]
        return max(past_dates) if past_dates else None

    def clean_filename(self, filename: str) -> str:
        """Clean filename from unwanted characters and patterns"""
        # Remove file extension
        name = Path(filename).stem

        # Remove common scan artifacts
        name = re.sub(r'[#_]*[Ss]canbot[#_]*', '', name)
        name = re.sub(r'[#_]*[Gg]escanntes?\s*[Dd]okument[#_]*', '', name)
        name = re.sub(r'[#_]*[Ss]can[#_]*', '', name)

        # Remove existing date patterns at the beginning
        name = re.sub(r'^[\d\-\.\/]+[_\s]*', '', name)

        # Remove multiple underscores/spaces
        name = re.sub(r'[_\s]+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        return name

    def generate_smart_filename(self, original_filename: str, text_content: str,
                              category: str, fallback_date: Optional[date] = None) -> str:
        """Generate intelligent filename with category and date"""

        # Extract dates from content
        dates = self.extract_dates_from_text(text_content)

        # Get the most relevant date
        target_date = self.get_most_recent_past_date(dates)

        # If no suitable date found in content, use fallback or today
        if not target_date:
            target_date = fallback_date or date.today()

        # Clean the original filename
        clean_name = self.clean_filename(original_filename)

        # Create category prefix (remove numbers and clean up)
        category_clean = re.sub(r'^\d+[_\s]*', '', category)  # Remove leading numbers
        category_clean = re.sub(r'[_\s]+', '_', category_clean)  # Normalize separators
        category_clean = category_clean.strip('_').lower()

        # Format date as YYYY-MM-DD
        date_str = target_date.strftime('%Y-%m-%d')

        # Combine parts
        if clean_name:
            new_filename = f"{date_str}_{category_clean}_{clean_name}.pdf"
        else:
            new_filename = f"{date_str}_{category_clean}_dokument.pdf"

        # Final cleanup
        new_filename = re.sub(r'[_]{2,}', '_', new_filename)  # Remove multiple underscores

        return new_filename

    def suggest_filename(self, original_filename: str, text_content: str,
                        category: str) -> dict:
        """Suggest a new filename and return detailed information"""

        # Extract dates
        dates = self.extract_dates_from_text(text_content)
        target_date = self.get_most_recent_past_date(dates)

        # Generate new filename
        new_filename = self.generate_smart_filename(original_filename, text_content, category)

        return {
            'original_filename': original_filename,
            'suggested_filename': new_filename,
            'extracted_dates': [d.isoformat() for d in dates],
            'selected_date': target_date.isoformat() if target_date else None,
            'category': category,
            'date_source': 'content' if target_date and dates else 'fallback'
        }


# Global instance
file_renaming_service = FileRenamingService()