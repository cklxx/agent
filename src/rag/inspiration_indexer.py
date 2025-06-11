# SPDX-License-Identifier: MIT

"""
Handles indexing of inspirational text content for later retrieval.
"""

import sqlite3
import os
import datetime
import logging
from typing import List, Tuple

# Setup logger
logger = logging.getLogger(__name__)

class InspirationIndexer:
    """
    Indexes textual inspirations from files into a SQLite database.
    Currently performs simple paragraph-based chunking and stores text directly.
    Future enhancements would include embedding generation and vector storage.
    """

    def __init__(self, db_path: str = "temp/rag_data/rag_inspirations.db"):
        """
        Initializes the InspirationIndexer and sets up the database.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to "temp/rag_data/rag_inspirations.db".
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        logger.info(f"InspirationIndexer initialized with database at {self.db_path}")

    def _init_db(self):
        """Initializes the database schema if it doesn't already exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inspirations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filepath TEXT NOT NULL,
                        chunk_text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.debug("Database schema initialized (or already exists).")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            raise

    def index_inspirations_from_directory(self, dir_path: str):
        """
        Scans a directory for .txt files, chunks their content, and indexes them.

        Args:
            dir_path: The path to the directory containing .txt inspiration files.
        """
        logger.info(f"Starting indexing of inspirations from directory: {dir_path}")
        if not os.path.isdir(dir_path):
            logger.error(f"Provided path is not a directory or does not exist: {dir_path}")
            return

        indexed_files_count = 0
        total_chunks_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for filename in os.listdir(dir_path):
                    if filename.endswith(".txt"):
                        filepath = os.path.join(dir_path, filename)
                        logger.debug(f"Processing file: {filepath}")
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                content = f.read()

                            # Simplified Chunking: Split by double newlines
                            chunks = content.split("\n\n")

                            chunks_for_db: List[Tuple[str, str]] = []
                            for i, chunk_text in enumerate(chunks):
                                chunk_text = chunk_text.strip()
                                if chunk_text: # Only index non-empty chunks
                                    # Placeholder for Embeddings
                                    chunk_preview = chunk_text[:100].replace("\n", " ") + "..."
                                    logger.debug(f"Embedding would be generated here for chunk ({i+1}/{len(chunks)}) from {filename}: {chunk_preview}")
                                    chunks_for_db.append((filepath, chunk_text))

                            if chunks_for_db:
                                cursor.executemany(
                                    "INSERT INTO inspirations (filepath, chunk_text) VALUES (?, ?)",
                                    chunks_for_db
                                )
                                conn.commit()
                                logger.info(f"Indexed {len(chunks_for_db)} chunks from {filename}.")
                                total_chunks_count += len(chunks_for_db)
                                indexed_files_count += 1
                            else:
                                logger.info(f"No non-empty chunks found in {filename}.")

                        except Exception as e:
                            logger.error(f"Failed to process or index file {filepath}: {e}", exc_info=True)
            logger.info(f"Finished indexing. Indexed {total_chunks_count} chunks from {indexed_files_count} files in {dir_path}.")
        except sqlite3.Error as e:
            logger.error(f"Database error during indexing: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred during directory indexing: {e}", exc_info=True)


if __name__ == '__main__':
    # Example Usage & Basic Test
    logging.basicConfig(level=logging.DEBUG)

    # Create a dummy inspirations directory and files for testing
    test_dir = "temp/test_inspirations"
    os.makedirs(test_dir, exist_ok=True)

    with open(os.path.join(test_dir, "idea1.txt"), "w") as f:
        f.write("This is the first brilliant idea.\n\nIt has multiple paragraphs for testing chunking.\n\nThis could be a plot point.")

    with open(os.path.join(test_dir, "theme_notes.txt"), "w") as f:
        f.write("Exploring themes of redemption.\n\nAnd the struggle between good and evil.\n\nAlso, the color blue is important.")

    with open(os.path.join(test_dir, "empty.txt"), "w") as f:
        f.write("") # Empty file

    with open(os.path.join(test_dir, "single_chunk.txt"), "w") as f:
        f.write("This is a single chunk of text without double newlines.")

    test_db_path = "temp/rag_data/test_rag_inspirations.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path) # Clean slate for testing

    indexer = InspirationIndexer(db_path=test_db_path)
    indexer.index_inspirations_from_directory(test_dir)

    # Verify by querying the DB directly (optional, for testing)
    try:
        conn_verify = sqlite3.connect(test_db_path)
        cursor_verify = conn_verify.cursor()
        cursor_verify.execute("SELECT filepath, chunk_text FROM inspirations")
        rows = cursor_verify.fetchall()
        logger.info(f"\n--- Verification: Content in DB ({test_db_path}) ---")
        for row in rows:
            logger.info(f"File: {row[0]}, Chunk Preview: {row[1][:70]}...")
        conn_verify.close()
        logger.info(f"--- Verification Complete. Found {len(rows)} chunks. ---")
    except sqlite3.Error as e:
        logger.error(f"Verification query failed: {e}")

    # Clean up dummy files (optional)
    # for f_name in os.listdir(test_dir):
    #     os.remove(os.path.join(test_dir, f_name))
    # os.rmdir(test_dir)
    # logger.info("Cleaned up test directory and files.")
```
