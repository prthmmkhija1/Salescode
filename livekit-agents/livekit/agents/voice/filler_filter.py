"""Filler word detection and filtering for intelligent interruption handling."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Sequence

logger = logging.getLogger(__name__)


@dataclass
class FillerFilterConfig:
    """Configuration for filler word filtering.
    
    Attributes:
        ignored_words: List of words/phrases to ignore during agent speech
        min_confidence: Minimum ASR confidence threshold (0.0-1.0)
        enabled: Whether filler filtering is enabled
    """
    ignored_words: list[str]
    min_confidence: float = 0.6
    enabled: bool = True


class FillerWordFilter:
    """Filters filler words to prevent false interruptions during agent speech."""
    
    DEFAULT_FILLER_WORDS = [
        # English fillers
        "uh", "um", "umm", "uhh", "hmm", "hm", "mhm", "mmm",
        "ah", "ahh", "er", "err", "like",
        # Hindi fillers
        "haan", "haa", "accha", "theek",
        # Spanish fillers
        "eh", "este", "pues",
        # French fillers
        "euh", "ben", "alors",
        # German fillers
        "äh", "ähm", "also",
    ]
    
    def __init__(self, config: FillerFilterConfig | None = None) -> None:
        """Initialize the filler word filter.
        
        Args:
            config: Filter configuration. If None, uses defaults from environment.
        """
        if config is None:
            config = self._load_config_from_env()
        
        self._config = config
        self._pattern = self._compile_pattern(config.ignored_words)
        
        logger.info(
            "FillerWordFilter initialized with %d words: %s",
            len(config.ignored_words),
            config.ignored_words,
        )
    
    @classmethod
    def _load_config_from_env(cls) -> FillerFilterConfig:
        """Load configuration from environment variables."""
        env_words = os.getenv("AGENT_FILLER_WORDS", "")
        
        if env_words:
            # Parse comma-separated list from environment
            ignored_words = [w.strip().lower() for w in env_words.split(",") if w.strip()]
        else:
            ignored_words = cls.DEFAULT_FILLER_WORDS.copy()
        
        min_confidence = float(os.getenv("AGENT_FILLER_MIN_CONFIDENCE", "0.6"))
        enabled = os.getenv("AGENT_FILLER_FILTER_ENABLED", "true").lower() == "true"
        
        return FillerFilterConfig(
            ignored_words=ignored_words,
            min_confidence=min_confidence,
            enabled=enabled,
        )
    
    def _compile_pattern(self, words: list[str]) -> re.Pattern:
        """Compile regex pattern for matching filler words.
        
        Args:
            words: List of filler words to match
            
        Returns:
            Compiled regex pattern
        """
        # Escape special regex characters and join with word boundaries
        escaped_words = [re.escape(word) for word in words]
        pattern = r'\b(' + '|'.join(escaped_words) + r')\b'
        return re.compile(pattern, re.IGNORECASE)
    
    def update_ignored_words(self, words: Sequence[str]) -> None:
        """Dynamically update the list of ignored filler words.
        
        Args:
            words: New list of words to ignore
        """
        self._config.ignored_words = list(words)
        self._pattern = self._compile_pattern(self._config.ignored_words)
        
        logger.info(
            "Filler word list updated: %d words - %s",
            len(words),
            words,
        )
    
    def add_ignored_words(self, words: Sequence[str]) -> None:
        """Add words to the existing ignored list.
        
        Args:
            words: Words to add to the ignored list
        """
        new_words = [w.lower().strip() for w in words if w.strip()]
        self._config.ignored_words.extend(new_words)
        # Remove duplicates while preserving order
        self._config.ignored_words = list(dict.fromkeys(self._config.ignored_words))
        self._pattern = self._compile_pattern(self._config.ignored_words)
        
        logger.info("Added %d filler words: %s", len(new_words), new_words)
    
    def is_only_filler(
        self,
        text: str,
        *,
        confidence: float | None = None,
    ) -> bool:
        """Check if the text contains only filler words.
        
        Args:
            text: Text to check
            confidence: Optional ASR confidence score (0.0-1.0)
            
        Returns:
            True if text is only fillers, False if it contains meaningful content
        """
        if not self._config.enabled:
            return False
        
        if not text or not text.strip():
            return True
        
        # Check confidence threshold
        if confidence is not None and confidence < self._config.min_confidence:
            logger.debug(
                "Low confidence transcript (%.2f < %.2f): treating as filler",
                confidence,
                self._config.min_confidence,
            )
            return True
        
        # Normalize text: lowercase and remove punctuation
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        if not normalized:
            return True
        
        # Remove all filler words
        cleaned = self._pattern.sub('', normalized)
        cleaned = cleaned.strip()
        
        # If nothing remains after removing fillers, it's filler-only
        is_filler = len(cleaned) == 0
        
        if is_filler:
            logger.debug(
                "Detected filler-only input: '%s' (confidence: %.2f)",
                text,
                confidence or 0.0,
            )
        
        return is_filler
    
    def contains_meaningful_content(
        self,
        text: str,
        *,
        confidence: float | None = None,
    ) -> bool:
        """Check if text contains meaningful content beyond fillers.
        
        This is the inverse of is_only_filler() for readability.
        
        Args:
            text: Text to check
            confidence: Optional ASR confidence score
            
        Returns:
            True if text contains meaningful words, False otherwise
        """
        return not self.is_only_filler(text, confidence=confidence)
    
    @property
    def config(self) -> FillerFilterConfig:
        """Get current filter configuration."""
        return self._config
    
    @property
    def ignored_words(self) -> list[str]:
        """Get list of currently ignored words."""
        return self._config.ignored_words.copy()