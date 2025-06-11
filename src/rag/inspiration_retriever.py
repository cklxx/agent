# SPDX-License-Identifier: MIT

"""
Retrieves inspirational text content from an indexed database.
"""

import sqlite3
import logging
from typing import List, Dict

# Setup logger
logger = logging.getLogger(__name__)

class InspirationRetriever:
    """
    Retrieves textual inspirations from a SQLite database.
    Currently uses simple SQL LIKE queries for retrieval.
    Future enhancements would involve semantic/vector search.
    """

    def __init__(self, db_path: str = "temp/rag_data/rag_inspirations.db"):
        """
        Initializes the InspirationRetriever.

        Args:
            db_path: Path to the SQLite database file where inspirations are indexed.
                     Defaults to "temp/rag_data/rag_inspirations.db".
        """
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.warning(f"Database file {self.db_path} does not exist. Retriever might not find any data.")
        logger.info(f"InspirationRetriever initialized with database at {self.db_path}")

    def retrieve_inspirations(self, query: str, count: int = 3) -> List[Dict[str, str]]:
        """
        Retrieves inspirations from the database based on a query string.
        Uses a simple SQL LIKE query to find matching chunks.

        Args:
            query: The search query string.
            count: The maximum number of inspirations to retrieve. Defaults to 3.

        Returns:
            A list of dictionaries, where each dictionary contains 'filepath' and 'chunk_text'.
            Returns an empty list if no matches are found or if an error occurs.
        """
        logger.debug(f"Retrieving up to {count} inspirations for query: '{query}'")
        results: List[Dict[str, str]] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Using FTS5 table would be much better for full-text search.
                # For now, a simple LIKE query.
                # The query is case-insensitive by default for LIKE in SQLite unless PRAGMA case_sensitive_like=ON;
                sql_query = "SELECT filepath, chunk_text FROM inspirations WHERE chunk_text LIKE ? ORDER BY created_at DESC LIMIT ?"

                # Add wildcards for LIKE query
                like_query = f"%{query}%"

                cursor.execute(sql_query, (like_query, count))
                rows = cursor.fetchall()

                for row in rows:
                    results.append({"filepath": str(row[0]), "chunk_text": str(row[1])})

                logger.info(f"Retrieved {len(results)} inspirations for query '{query}'.")
        except sqlite3.Error as e:
            logger.error(f"Database error during inspiration retrieval: {e}", exc_info=True)
            # Return empty list on error
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during inspiration retrieval: {e}", exc_info=True)
            return []

        return results

if __name__ == '__main__':
    # Example Usage & Basic Test (assumes a DB has been created by InspirationIndexer)
    import os # Required for os.path.exists

    logging.basicConfig(level=logging.DEBUG)

    test_db_path = "temp/rag_data/test_rag_inspirations.db" # Should match the test DB from indexer

    if not os.path.exists(test_db_path):
        logger.error(f"Test database {test_db_path} not found. Run the indexer example first.")
    else:
        retriever = InspirationRetriever(db_path=test_db_path)

        logger.info("\n--- Testing Retrieval ---")

        queries_to_test = ["idea", "redemption", "color blue", "multiple paragraphs", "nonexistent"]

        for q in queries_to_test:
            logger.info(f"\nQuerying for: '{q}'")
            inspirations = retriever.retrieve_inspirations(q, count=2)
            if inspirations:
                for i, insp in enumerate(inspirations):
                    logger.info(f"  Result {i+1}:")
                    logger.info(f"    File: {insp['filepath']}")
                    logger.info(f"    Chunk: {insp['chunk_text'][:100]}...")
            else:
                logger.info(f"  No results found for '{q}'.")

        logger.info("\n--- Retrieval Test Finished ---")

```
