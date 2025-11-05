"""
Player name matching utilities using fuzzy matching and common name variations.
"""
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
import re


class NameMatcher:
    """Handles player name matching between different data sources."""
    
    # Common suffixes and their variations
    SUFFIX_VARIATIONS = {
        'jr.': ['jr', 'jr.', 'junior'],
        'sr.': ['sr', 'sr.', 'senior'],
        'ii': ['ii', '2', 'the second'],
        'iii': ['iii', '3', 'the third'],
        'iv': ['iv', '4', 'the fourth'],
        'v': ['v', '5', 'the fifth'],
    }
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize a player name for comparison.
        
        Args:
            name: Player name to normalize
            
        Returns:
            Normalized name (lowercase, trimmed, single spaces)
        """
        if not name:
            return ""
        
        # Convert to lowercase and strip
        name = name.lower().strip()
        
        # Remove multiple spaces
        name = " ".join(name.split())
        
        # Remove common punctuation
        name = name.replace(".", "").replace("'", "").replace("-", " ")
        
        # Normalize suffixes
        for standard, variations in NameMatcher.SUFFIX_VARIATIONS.items():
            for var in variations:
                pattern = r'\b' + re.escape(var) + r'\b'
                name = re.sub(pattern, standard.replace('.', ''), name)
        
        return name
    
    @staticmethod
    def strip_suffix(name: str) -> str:
        """
        Remove common suffixes from name.
        
        Args:
            name: Player name
            
        Returns:
            Name without suffix
        """
        normalized = NameMatcher.normalize_name(name)
        
        # Remove known suffixes
        for standard, variations in NameMatcher.SUFFIX_VARIATIONS.items():
            for var in [standard.replace('.', '')] + variations:
                pattern = r'\b' + re.escape(var) + r'\b'
                normalized = re.sub(pattern, '', normalized)
        
        return " ".join(normalized.split()).strip()
    
    @staticmethod
    def similarity_score(name1: str, name2: str) -> float:
        """
        Calculate similarity score between two names (0.0 to 1.0).
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity score between 0 and 1
        """
        norm1 = NameMatcher.normalize_name(name1)
        norm2 = NameMatcher.normalize_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Try exact match first
        if norm1 == norm2:
            return 1.0
        
        # Try without suffixes
        stripped1 = NameMatcher.strip_suffix(name1)
        stripped2 = NameMatcher.strip_suffix(name2)
        
        if stripped1 == stripped2 and stripped1:
            return 0.95
        
        # Use sequence matcher for fuzzy matching
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    @staticmethod
    def find_best_match(
        target_name: str,
        candidate_names: List[str],
        threshold: float = 0.85
    ) -> Optional[Tuple[str, float]]:
        """
        Find the best matching name from a list of candidates.
        
        Args:
            target_name: Name to match
            candidate_names: List of candidate names
            threshold: Minimum similarity score to consider (default: 0.85)
            
        Returns:
            Tuple of (best_match_name, score) or None if no good match found
        """
        if not target_name or not candidate_names:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidate_names:
            score = NameMatcher.similarity_score(target_name, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score >= threshold:
            return (best_match, best_score)
        
        return None
    
    @staticmethod
    def build_name_map(
        source_names: List[str],
        target_names: List[str],
        threshold: float = 0.85
    ) -> Dict[str, str]:
        """
        Build a mapping between two lists of names using fuzzy matching.
        
        Args:
            source_names: Names to map from
            target_names: Names to map to
            threshold: Minimum similarity score (default: 0.85)
            
        Returns:
            Dictionary mapping source names to target names
        """
        name_map = {}
        
        for source_name in source_names:
            match = NameMatcher.find_best_match(source_name, target_names, threshold)
            if match:
                name_map[source_name] = match[0]
        
        return name_map

