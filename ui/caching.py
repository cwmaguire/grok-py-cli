"""
Response Caching and History Management Module

Provides efficient caching of responses and history management for the Grok CLI,
including memory optimization, quick access, and persistence.
"""

import asyncio
import hashlib
import json
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Deque
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
from concurrent.futures import ThreadPoolExecutor

# Assuming logger is available
try:
    from ..utils.logging import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)


@dataclass
class CachedResponse:
    """Represents a cached response with metadata."""
    key: str
    content: str
    response_type: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 1
    size_bytes: int = 0

    def __post_init__(self):
        self.size_bytes = len(self.content.encode('utf-8')) + len(json.dumps(self.metadata).encode('utf-8'))


@dataclass
class HistoryEntry:
    """Represents a history entry for chat conversations."""
    id: str
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseCache:
    """
    In-memory cache for responses with LRU eviction and optional persistence.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 50,
        ttl_seconds: int = 3600,  # 1 hour
        persistence_path: Optional[str] = None
    ):
        """
        Initialize the response cache.

        Args:
            max_size: Maximum number of cached items
            max_memory_mb: Maximum memory usage in MB
            ttl_seconds: Time-to-live for cache entries
            persistence_path: Path for persistent storage
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds
        self.persistence_path = Path(persistence_path) if persistence_path else None

        # Thread-safe storage
        self._cache: OrderedDict[str, CachedResponse] = OrderedDict()
        self._lock = threading.RLock()
        self._current_memory = 0

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        # Background cleanup
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cache")
        self._cleanup_task: Optional[asyncio.Task] = None

        # Load persistent cache if available
        if self.persistence_path:
            self._load_persistent_cache()

    def generate_key(self, request_data: Dict[str, Any]) -> str:
        """
        Generate a cache key from request data.

        Args:
            request_data: Request data to hash

        Returns:
            Cache key string
        """
        # Create a normalized version for consistent hashing
        normalized = self._normalize_request_data(request_data)
        key_data = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]

    def _normalize_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize request data for consistent hashing."""
        # Remove timestamps and non-deterministic fields
        normalized = {}
        for key, value in data.items():
            if key not in ['timestamp', 'request_id', 'stream']:
                if isinstance(value, dict):
                    normalized[key] = self._normalize_request_data(value)
                elif isinstance(value, list):
                    normalized[key] = [self._normalize_request_data(item) if isinstance(item, dict) else item for item in value]
                else:
                    normalized[key] = value
        return normalized

    def get(self, key: str) -> Optional[CachedResponse]:
        """
        Get a cached response.

        Args:
            key: Cache key

        Returns:
            Cached response or None
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # Check TTL
                if time.time() - entry.created_at > self.ttl_seconds:
                    self._remove_entry(key)
                    self.misses += 1
                    return None

                # Update access stats
                entry.accessed_at = time.time()
                entry.access_count += 1
                self._cache.move_to_end(key)  # Mark as recently used
                self.hits += 1
                return entry

            self.misses += 1
            return None

    def put(self, key: str, response: CachedResponse) -> None:
        """
        Store a response in cache.

        Args:
            key: Cache key
            response: Response to cache
        """
        with self._lock:
            # Check if we need to evict
            while (len(self._cache) >= self.max_size or
                   self._current_memory + response.size_bytes > self.max_memory_bytes):
                self._evict_lru()

            # Add new entry
            self._cache[key] = response
            self._cache.move_to_end(key)
            self._current_memory += response.size_bytes

            # Schedule persistence if enabled
            if self.persistence_path:
                self._executor.submit(self._save_entry, key, response)

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)  # FIFO (LRU)
            self._current_memory -= entry.size_bytes
            self.evictions += 1
            logger.debug(f"Evicted cache entry: {key}")

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory -= entry.size_bytes

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self.hits = self.misses = self.evictions = 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_entries = len(self._cache)
            total_memory_mb = self._current_memory / (1024 * 1024)
            hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0

            return {
                "total_entries": total_entries,
                "memory_usage_mb": round(total_memory_mb, 2),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "hit_rate": round(hit_rate, 3),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "avg_entry_size_kb": round(total_memory_mb / max(total_entries, 1) * 1024, 2)
            }

    def _load_persistent_cache(self) -> None:
        """Load cache from persistent storage."""
        if not self.persistence_path.exists():
            return

        try:
            with sqlite3.connect(str(self.persistence_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key, content, response_type, tool_calls, metadata,
                           created_at, accessed_at, access_count
                    FROM cache_entries
                    WHERE ? - created_at < ?
                ''', (time.time(), self.ttl_seconds))

                for row in cursor.fetchall():
                    key, content, resp_type, tool_calls_json, metadata_json, created_at, accessed_at, access_count = row

                    try:
                        tool_calls = json.loads(tool_calls_json) if tool_calls_json else []
                        metadata = json.loads(metadata_json) if metadata_json else {}

                        entry = CachedResponse(
                            key=key,
                            content=content,
                            response_type=resp_type,
                            tool_calls=tool_calls,
                            metadata=metadata,
                            created_at=created_at,
                            accessed_at=accessed_at,
                            access_count=access_count
                        )

                        # Only load if it fits in memory
                        if self._current_memory + entry.size_bytes <= self.max_memory_bytes:
                            self._cache[key] = entry
                            self._current_memory += entry.size_bytes

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to load cache entry {key}: {e}")

        except Exception as e:
            logger.error(f"Failed to load persistent cache: {e}")

    def _save_entry(self, key: str, entry: CachedResponse) -> None:
        """Save an entry to persistent storage."""
        if not self.persistence_path:
            return

        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(str(self.persistence_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        content TEXT,
                        response_type TEXT,
                        tool_calls TEXT,
                        metadata TEXT,
                        created_at REAL,
                        accessed_at REAL,
                        access_count INTEGER
                    )
                ''')

                conn.execute('''
                    INSERT OR REPLACE INTO cache_entries
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    key, entry.content, entry.response_type,
                    json.dumps(entry.tool_calls), json.dumps(entry.metadata),
                    entry.created_at, entry.accessed_at, entry.access_count
                ))

        except Exception as e:
            logger.error(f"Failed to save cache entry {key}: {e}")

    def cleanup_expired(self) -> None:
        """Clean up expired entries."""
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if current_time - entry.created_at > self.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_entry(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def start_background_cleanup(self, interval_seconds: int = 300) -> None:
        """
        Start background cleanup task.

        Args:
            interval_seconds: Cleanup interval
        """
        if self._cleanup_task and not self._cleanup_task.done():
            return

        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, self.cleanup_expired
                    )
                except Exception as e:
                    logger.error(f"Background cleanup failed: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    def shutdown(self) -> None:
        """Shutdown the cache."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        self._executor.shutdown(wait=True)


class HistoryManager:
    """
    Manages chat history with efficient storage and retrieval.
    """

    def __init__(
        self,
        max_entries: int = 10000,
        persistence_path: Optional[str] = None,
        compression_threshold: int = 1000  # Compress after this many entries
    ):
        """
        Initialize the history manager.

        Args:
            max_entries: Maximum number of history entries
            persistence_path: Path for persistent storage
            compression_threshold: When to compress old entries
        """
        self.max_entries = max_entries
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.compression_threshold = compression_threshold

        # Thread-safe storage using deque for efficient FIFO
        self._history: Deque[HistoryEntry] = deque(maxlen=max_entries)
        self._lock = threading.RLock()

        # Quick access by ID
        self._id_index: Dict[str, HistoryEntry] = {}

        # Statistics
        self.total_entries = 0
        self.compressed_entries = 0

        # Load persistent history if available
        if self.persistence_path:
            self._load_persistent_history()

    def add_entry(self, entry: HistoryEntry) -> None:
        """
        Add a history entry.

        Args:
            entry: History entry to add
        """
        with self._lock:
            # Remove old entry if ID exists
            if entry.id in self._id_index:
                old_entry = self._id_index[entry.id]
                try:
                    self._history.remove(old_entry)
                except ValueError:
                    pass  # May have been evicted

            # Add new entry
            self._history.append(entry)
            self._id_index[entry.id] = entry
            self.total_entries += 1

            # Compress if needed
            if len(self._history) > self.compression_threshold:
                self._compress_old_entries()

            # Persist if enabled
            if self.persistence_path:
                self._executor.submit(self._save_entry, entry)

    def get_entry(self, entry_id: str) -> Optional[HistoryEntry]:
        """
        Get a history entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            History entry or None
        """
        with self._lock:
            return self._id_index.get(entry_id)

    def get_recent_entries(self, limit: int = 50) -> List[HistoryEntry]:
        """
        Get recent history entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent entries (newest first)
        """
        with self._lock:
            return list(self._history)[-limit:]

    def search_entries(
        self,
        query: str,
        role: Optional[str] = None,
        limit: int = 20
    ) -> List[HistoryEntry]:
        """
        Search history entries.

        Args:
            query: Search query (case-insensitive substring)
            role: Filter by role
            limit: Maximum results

        Returns:
            Matching entries
        """
        results = []
        query_lower = query.lower()

        with self._lock:
            for entry in reversed(self._history):  # Search from newest
                if role and entry.role != role:
                    continue

                if query_lower in entry.content.lower():
                    results.append(entry)
                    if len(results) >= limit:
                        break

        return results

    def clear_history(self) -> None:
        """Clear all history."""
        with self._lock:
            self._history.clear()
            self._id_index.clear()
            self.total_entries = 0
            self.compressed_entries = 0

    def _compress_old_entries(self) -> None:
        """Compress old entries to save memory."""
        if len(self._history) < self.compression_threshold:
            return

        # Keep only recent entries uncompressed
        keep_count = min(self.max_entries // 2, self.compression_threshold // 2)
        entries_to_compress = len(self._history) - keep_count

        if entries_to_compress > 0:
            # Mark old entries as compressed (could implement actual compression)
            for i in range(entries_to_compress):
                entry = self._history[i]
                if not entry.metadata.get('compressed', False):
                    entry.metadata['compressed'] = True
                    # Could compress content here
                    self.compressed_entries += 1

            logger.debug(f"Compressed {entries_to_compress} old history entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get history statistics.

        Returns:
            Dictionary with history stats
        """
        with self._lock:
            return {
                "total_entries": self.total_entries,
                "current_entries": len(self._history),
                "max_entries": self.max_entries,
                "compressed_entries": self.compressed_entries,
                "compression_ratio": self.compressed_entries / max(self.total_entries, 1),
                "memory_usage_mb": self._estimate_memory_usage() / (1024 * 1024)
            }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of history."""
        total_size = 0
        for entry in self._history:
            total_size += (
                len(entry.content.encode('utf-8')) +
                len(json.dumps(entry.metadata).encode('utf-8')) +
                256  # Overhead per entry
            )
        return total_size

    def _load_persistent_history(self) -> None:
        """Load history from persistent storage."""
        if not self.persistence_path.exists():
            return

        try:
            with sqlite3.connect(str(self.persistence_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, role, content, timestamp, metadata
                    FROM history_entries
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (self.max_entries,))

                for row in cursor.fetchall():
                    entry_id, role, content, timestamp, metadata_json = row

                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}

                        entry = HistoryEntry(
                            id=entry_id,
                            role=role,
                            content=content,
                            timestamp=timestamp,
                            metadata=metadata
                        )

                        self._history.appendleft(entry)  # Add to front (oldest first)
                        self._id_index[entry_id] = entry

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to load history entry {entry_id}: {e}")

                self.total_entries = len(self._history)

        except Exception as e:
            logger.error(f"Failed to load persistent history: {e}")

    def _save_entry(self, entry: HistoryEntry) -> None:
        """Save an entry to persistent storage."""
        if not self.persistence_path:
            return

        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(str(self.persistence_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS history_entries (
                        id TEXT PRIMARY KEY,
                        role TEXT,
                        content TEXT,
                        timestamp REAL,
                        metadata TEXT
                    )
                ''')

                conn.execute('''
                    INSERT OR REPLACE INTO history_entries
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    entry.id, entry.role, entry.content,
                    entry.timestamp, json.dumps(entry.metadata)
                ))

        except Exception as e:
            logger.error(f"Failed to save history entry {entry.id}: {e}")

    # Initialize executor for persistence
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="history")