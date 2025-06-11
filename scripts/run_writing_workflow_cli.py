# SPDX-License-Identifier: MIT

"""
Command-Line Interface for running the Writing Inspiration Workflow.

This script allows users to invoke the writing inspiration workflow
with a task description and optionally specify the maximum iterations for the agent.
"""

import asyncio
import logging
import argparse
import json # For pretty printing results

# Attempt to import the specific workflow runner
try:
    from src.writing_inspiration_workflow import run_writing_inspiration_workflow
except ImportError:
    print("Error: Could not import 'run_writing_inspiration_workflow'. ")
    print("Ensure you are running this script from the root of the project directory,")
    print("and that the 'src' directory is in your PYTHONPATH if necessary.")
    exit(1)

# Attempt to import a structured logging configuration
try:
    from src.config.logging_config import configure_logging
    LOGGING_CONFIG_AVAILABLE = True
except ImportError:
    LOGGING_CONFIG_AVAILABLE = False
    # Basic logging will be used if configure_logging is not found

# Logger for this script
logger = logging.getLogger(__name__)

async def main():
    """
    Parses command-line arguments and runs the writing inspiration workflow.
    """
    if LOGGING_CONFIG_AVAILABLE:
        configure_logging() # Apply structured logging if available
        logger.info("Structured logging configured.")
    else:
        # Fallback to basic logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        logger.info("Using basic logging configuration.")

    parser = argparse.ArgumentParser(
        description="Run the Writing Inspiration Workflow with a given task description."
    )
    parser.add_argument(
        "task_description",
        type=str,
        help="The user's creative writing request or task description."
    )
    parser.add_argument(
        "--max_iterations",
        type=int,
        default=10, # Defaulting to a slightly higher value for CLI, can be adjusted
        help="Maximum number of iterations for the agent per step (default: 10)."
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help="Optional path to a JSON file to save the results."
    )


    args = parser.parse_args()

    logger.info(f"Received task: \"{args.task_description}\"")
    logger.info(f"Maximum iterations per step: {args.max_iterations}")

    try:
        results = await run_writing_inspiration_workflow(
            args.task_description,
            args.max_iterations
        )

        print("\n--- Workflow Results ---")
        # Pretty print the JSON results
        print(json.dumps(results, indent=2, default=str)) # Use default=str for non-serializable types like datetime

        if args.output_file:
            logger.info(f"Saving results to {args.output_file}...")
            try:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results successfully saved to {args.output_file}")
            except IOError as e:
                logger.error(f"Error saving results to file: {e}")


    except ImportError as e:
        logger.error(f"An import error occurred: {e}. This might be due to an incomplete setup or missing dependencies.")
        logger.error("Please ensure all required packages are installed and the script is run from the project root.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while running the workflow: {e}", exc_info=True)
        print(f"\nAn error occurred: {e}")
        print("Check the logs for more details.")

if __name__ == "__main__":
    # Ensure the script is run with Python 3.7+ for asyncio.run
    # For older versions, one might use loop = asyncio.get_event_loop(); loop.run_until_complete(main())
    asyncio.run(main())
```
