"""
Glossary builder that creates a searchable index from the medical dataset.
"""
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# Module-level cache for glossary data (avoid reloading 85k records per request)
_GLOSSARY_CACHE: dict | None = None
_DATASET_CACHE: pd.DataFrame | None = None


class GlossaryBuilder:
    """
    Builds and maintains a searchable glossary from the medical dataset.
    Uses the PLABA and Cochrane datasets which contain technical -> simple translations.
    
    Note: Uses module-level caching to avoid reloading 85k records per request.
    """
    
    def __init__(self, dataset_path: Optional[str] = None):
        """
        Initialize the glossary builder.
        
        Args:
            dataset_path: Path to the merged_plain_language_dataset.csv file.
                         If None, tries to find it in the repo root.
        """
        global _GLOSSARY_CACHE, _DATASET_CACHE
        
        if dataset_path is None:
            # Try to find dataset in data folder
            # Current file: backend/src/services/summaries/glossary_builder.py
            # 5 parents up to reach hack-4-health-2026-radiohead
            repo_root = Path(__file__).parent.parent.parent.parent.parent
            dataset_path = repo_root / "data" / "merged_plain_language_dataset.csv"
            
            # Fallback for different working environments
            if not dataset_path.exists():
                dataset_path = Path("data") / "merged_plain_language_dataset.csv"
        
        self.dataset_path = Path(dataset_path).absolute()
        
        # Use cached data if available
        if _GLOSSARY_CACHE is not None:
            self.glossary = _GLOSSARY_CACHE
            self._dataset_df = _DATASET_CACHE
            self._loaded = True
            logger.info("Using cached glossary (skipped CSV reload)")
        else:
            self.glossary: Dict[str, str] = {}
            self._dataset_df: Optional[pd.DataFrame] = None
            self._loaded = False
        
    def load_dataset(self) -> pd.DataFrame:
        """
        Load the dataset CSV file.
        
        Returns:
            DataFrame with the dataset
        """
        if self._dataset_df is not None:
            return self._dataset_df
            
        if not self.dataset_path.exists():
            logger.warning(f"Dataset not found at {self.dataset_path}. RAG will not work.")
            return pd.DataFrame()
        
        try:
            logger.info(f"Loading medical glossary dataset from {self.dataset_path}")
            df = pd.read_csv(self.dataset_path)
            logger.info(f"Loaded {len(df):,} records from dataset")
            
            # Log source distribution
            if 'source_dataset' in df.columns:
                source_counts = df['source_dataset'].value_counts()
                logger.info(f"Source datasets: {source_counts.to_dict()}")
            
            self._dataset_df = df
            self._loaded = True
            return df
        except Exception as e:
            logger.error(f"Error loading dataset: {str(e)}")
            return pd.DataFrame()
    
    def build_glossary(self, preferred_sources: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Build a glossary dictionary from the dataset.
        Extracts technical terms and their plain language definitions.
        
        Args:
            preferred_sources: List of preferred source datasets (e.g., ['PLABA', 'Cochrane']).
                              If None, uses all sources.
        
        Returns:
            Dictionary mapping technical terms to plain language definitions
        """
        df = self.load_dataset()
        
        if df.empty:
            logger.warning("Dataset is empty. Cannot build glossary.")
            return {}
        
        # Filter by preferred sources if specified
        if preferred_sources and 'source_dataset' in df.columns:
            df_filtered = df[df['source_dataset'].isin(preferred_sources)].copy()
            if not df_filtered.empty:
                logger.info(f"Filtered to {len(df_filtered):,} records from preferred sources: {preferred_sources}")
                df = df_filtered
        
        glossary = {}
        
        # Check required columns
        if 'original_text' not in df.columns or 'plain_language_text' not in df.columns:
            logger.error("Dataset missing required columns: 'original_text' or 'plain_language_text'")
            return {}
        
        # Extract term-definition pairs
        # Strategy: Use original_text as the "technical term" and plain_language_text as the definition
        # For short original texts, treat them as terms to define
        for idx, row in df.iterrows():
            original = str(row.get('original_text', '')).strip()
            plain = str(row.get('plain_language_text', '')).strip()
            
            if not original or not plain:
                continue
            
            # For short technical phrases (likely terms), add them to glossary
            # For longer texts, extract key terms from original_text
            if len(original) < 200:  # Short enough to be a term/phrase
                # Normalize the term (lowercase, remove extra spaces)
                term = ' '.join(original.lower().split())
                if term and term not in glossary:
                    glossary[term] = plain
            else:
                # For longer texts, extract potential medical terms
                # Simple approach: extract capitalized words/phrases
                import re
                # Find medical terms (capitalized words, abbreviations, etc.)
                terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', original)
                for term in terms:
                    term_lower = term.lower()
                    if len(term) > 3 and term_lower not in glossary:
                        glossary[term_lower] = plain
        
        logger.info(f"Built glossary with {len(glossary):,} term definitions")
        self.glossary = glossary
        
        # Save to module-level cache for future instances
        global _GLOSSARY_CACHE, _DATASET_CACHE
        _GLOSSARY_CACHE = glossary
        _DATASET_CACHE = self._dataset_df
        
        return glossary
    
    def search_term(self, term: str, threshold: int = 80) -> Optional[Tuple[str, str]]:
        """
        Search for a term in the glossary using fuzzy matching.
        
        Args:
            term: The term to search for
            threshold: Minimum similarity score (0-100) for a match
        
        Returns:
            Tuple of (matched_term, definition) if found, None otherwise
        """
        if not self.glossary:
            self.build_glossary()
        
        if not self.glossary:
            return None
        
        term_lower = term.lower().strip()
        
        # Exact match first
        if term_lower in self.glossary:
            return (term, self.glossary[term_lower])
        
        # Fuzzy match
        result = process.extractOne(
            term_lower,
            self.glossary.keys(),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold
        )
        
        if result:
            matched_term, score, _ = result
            return (matched_term, self.glossary[matched_term])
        
        return None
    
    def search_terms(self, terms: List[str], threshold: int = 80) -> Dict[str, str]:
        """
        Search for multiple terms and return definitions.
        
        Args:
            terms: List of terms to search for
            threshold: Minimum similarity score for matches
        
        Returns:
            Dictionary mapping terms to their definitions
        """
        definitions = {}
        
        for term in terms:
            if not term or len(term.strip()) < 2:
                continue
            
            result = self.search_term(term, threshold)
            if result:
                matched_term, definition = result
                definitions[term] = definition
        
        return definitions
    
    def get_dataset_records(self, search_text: str, limit: int = 5) -> List[Dict]:
        """
        Search the dataset directly for records containing the search text.
        Useful for finding contextual definitions.
        
        Args:
            search_text: Text to search for in original_text
            limit: Maximum number of results to return
        
        Returns:
            List of matching records
        """
        df = self.load_dataset()
        
        if df.empty:
            return []
        
        if 'original_text' not in df.columns:
            return []
        
        # Simple text search (case-insensitive)
        mask = df['original_text'].str.contains(search_text, case=False, na=False)
        matches = df[mask].head(limit)
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                'original_text': row.get('original_text', ''),
                'plain_language_text': row.get('plain_language_text', ''),
                'source_dataset': row.get('source_dataset', 'Unknown')
            })
        
        return results
