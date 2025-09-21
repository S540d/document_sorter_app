"""
File Renaming Service
Handles intelligent file renaming based on category and extracted dates
"""

import re
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict
from pathlib import Path


class FileRenamingService:
    """Service for intelligent file renaming"""

    def __init__(self):
        # German date patterns (4-digit years first to avoid ambiguity)
        self.date_patterns = [
            # DD.MM.YYYY or DD/MM/YYYY (prioritize 4-digit years)
            r'(\d{1,2})[./](\d{1,2})[./](\d{4})',
            # YYYY-MM-DD (ISO format)
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # Month names in German with 4-digit years
            r'(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*(\d{4})',
            # Month abbreviations with 4-digit years
            r'(\d{1,2})\.\s*(Jan|Feb|Mär|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\s*(\d{4})',
            # DD.MM.YY or DD/MM/YY (only if no 4-digit year found)
            r'(\d{1,2})[./](\d{1,2})[./](\d{2})(?!\d)',
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
                        elif pattern == self.date_patterns[4]:  # DD.MM.YY (last pattern)
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
        """Get the most recent date that is in the past or most relevant document date"""
        if not dates:
            return None

        today = date.today()

        # Filter out clearly invalid future dates (more than 1 year in future)
        reasonable_dates = [d for d in dates if d <= today + timedelta(days=365)]

        if not reasonable_dates:
            return None

        # For documents, prefer dates that are not too far in the future
        past_dates = [d for d in reasonable_dates if d <= today]

        if past_dates:
            return max(past_dates)
        else:
            # If no past dates, return the earliest reasonable future date
            return min(reasonable_dates)

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

    def extract_title_from_text(self, text: str) -> Optional[str]:
        """Extract meaningful title/heading from PDF text"""
        if not text:
            return None

        lines = text.split('\n')

        # Common patterns for document titles - improved flexibility
        title_patterns = [
            # Look for lines starting with specific document type keywords
            r'^(Rechnung|Invoice|Mahnung|Mitteilung|Bescheid|Nachweis|Zeugnis|Vertrag|Vereinbarung|Bestätigung|Anschreiben|Brief|Schreiben|Kündigung|Anmeldung|Abmeldung|Antrag).*',
            # Look for lines containing important document keywords (anywhere in line)
            r'.*(KÜNDIGUNG|VERTRAG|RECHNUNG|MAHNUNG|BESCHEID|NACHWEIS|BESTÄTIGUNG|ANMELDUNG|ABMELDUNG).*',
            # Look for lines that are all caps and short (likely titles)
            r'^[A-ZÄÖÜ\s\-\.]{8,50}$',
            # Look for lines with specific formatting (bold indicators)
            r'^\*\*.*\*\*$',
            # Look for numbered documents
            r'^[\d\.\-\s]*(Rechnung|Dokument|Nachweis|Bescheid|Kündigung).*',
        ]

        potential_titles = []

        # Check first 10 lines for titles
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line or len(line) < 5:
                continue

            # Skip common header/footer elements
            if any(skip in line.lower() for skip in ['seite', 'page', 'datum', 'von:', 'an:', 'betreff:']):
                continue

            # Check if line matches title patterns
            for pattern in title_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    potential_titles.append((line, i))
                    break

            # Also consider lines that are significantly shorter than surrounding text
            if 10 <= len(line) <= 60 and i < 5:
                # Check if it's likely a title (not too many numbers, not email/url)
                if not re.search(r'[\d]{4,}|@|\.(com|de|org)', line):
                    word_count = len(line.split())
                    if 2 <= word_count <= 8:
                        potential_titles.append((line, i))

        # Look for the best title (prefer earlier, cleaner ones)
        if potential_titles:
            # Sort by position (earlier is better) and length (moderate length preferred)
            potential_titles.sort(key=lambda x: (x[1], abs(len(x[0]) - 25)))
            return self.clean_title(potential_titles[0][0])

        return None

    def clean_title(self, title: str) -> str:
        """Clean extracted title for use in filename"""
        if not title:
            return ""

        # Remove common prefixes/suffixes
        title = re.sub(r'^(Rechnung|Invoice|Nr\.|Nummer|Document|Dokument)[\s\:\-]*', '', title, flags=re.IGNORECASE)

        # Remove dates and numbers at the end
        title = re.sub(r'[\s\-]*\d{1,2}[\./]\d{1,2}[\./]\d{2,4}.*$', '', title)
        title = re.sub(r'[\s\-]*\d{4,}.*$', '', title)

        # Clean special characters for filename
        title = re.sub(r'[^\w\säöüÄÖÜß\-]', '', title)

        # Normalize whitespace and convert to underscores
        title = re.sub(r'\s+', '_', title.strip())

        # Limit length
        if len(title) > 40:
            title = title[:40].rstrip('_')

        return title.lower()

    def extract_subject_keywords(self, text: str) -> List[str]:
        """Extract subject-specific keywords that could be useful for filename"""
        keywords = []

        # Common document types and their keywords - expanded
        keyword_patterns = {
            'gehaltsnachweise': r'(gehalt|lohn|entgelt|vergütung|salary)',
            'rechnung': r'(rechnung|invoice|betrag|zahlung|payment)',
            'vertrag': r'(vertrag|contract|vereinbarung|agreement)',
            'mahnung': r'(mahnung|reminder|zahlungsaufforderung)',
            'bescheid': r'(bescheid|notice|mitteilung|information)',
            'nachweis': r'(nachweis|bestätigung|confirmation|certificate)',
            'kündigung': r'(kündigung|termination|beendigung|auflösung)',
            'bewerbung': r'(bewerbung|application|lebenslauf|cv)',
            'anmeldung': r'(anmeldung|registration|registrierung)',
            'abmeldung': r'(abmeldung|deregistration|austritt)',
            'antrag': r'(antrag|application|request|gesuch)',
            'mitteilung': r'(mitteilung|notification|benachrichtigung)',
        }

        text_lower = text.lower()
        for keyword, pattern in keyword_patterns.items():
            if re.search(pattern, text_lower):
                keywords.append(keyword)

        return keywords

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

        # Try to extract meaningful title from PDF content
        extracted_title = self.extract_title_from_text(text_content)

        # Extract subject keywords
        subject_keywords = self.extract_subject_keywords(text_content)

        # Clean the original filename as fallback
        clean_name = self.clean_filename(original_filename)

        # Create category prefix (remove numbers and clean up)
        category_clean = re.sub(r'^\d+[_\s]*', '', category)  # Remove leading numbers
        category_clean = re.sub(r'[_\s]+', '_', category_clean)  # Normalize separators
        category_clean = category_clean.strip('_').lower()

        # Format date as YYYY-MM-DD
        date_str = target_date.strftime('%Y-%m-%d')

        # Build filename components
        components = [date_str]

        # Skip category - user requested removal
        # if category_clean:
        #     components.append(category_clean)

        # Choose best name component (priority: extracted title > subject keywords > cleaned original)
        if extracted_title:
            components.append(extracted_title)
        elif subject_keywords:
            # Use the first relevant keyword
            components.append(subject_keywords[0])
        elif clean_name:
            components.append(clean_name)
        else:
            components.append('dokument')

        # Combine parts
        new_filename = '_'.join(components) + '.pdf'

        # Final cleanup
        new_filename = re.sub(r'[_]{2,}', '_', new_filename)  # Remove multiple underscores
        new_filename = re.sub(r'^_+|_+$', '', new_filename)  # Remove leading/trailing underscores

        return new_filename

    def suggest_filename(self, original_filename: str, text_content: str,
                        category: str) -> dict:
        """Suggest a new filename and return detailed information"""

        # Extract dates
        dates = self.extract_dates_from_text(text_content)
        target_date = self.get_most_recent_past_date(dates)

        # Extract title and keywords
        extracted_title = self.extract_title_from_text(text_content)
        subject_keywords = self.extract_subject_keywords(text_content)

        # Generate new filename
        new_filename = self.generate_smart_filename(original_filename, text_content, category)

        return {
            'original_filename': original_filename,
            'suggested_filename': new_filename,
            'extracted_dates': [d.isoformat() for d in dates],
            'selected_date': target_date.isoformat() if target_date else None,
            'category': category,
            'date_source': 'content' if target_date and dates else 'fallback',
            'extracted_title': extracted_title,
            'subject_keywords': subject_keywords,
            'title_source': 'pdf_content' if extracted_title else 'keywords' if subject_keywords else 'filename'
        }


# Global instance
file_renaming_service = FileRenamingService()