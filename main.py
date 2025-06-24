# SPDX-License-Identifier: MIT

"""
Entry point script for the DeepTool project.
"""

import argparse
import asyncio

from InquirerPy import inquirer

from src.config.questions import BUILT_IN_QUESTIONS, BUILT_IN_QUESTIONS_ZH_CN
from src.workflow import run_research_agent_async


def ask(
    question,
    debug=False,
    max_research_iterations=3,
    enable_background_investigation=True,
    auto_execute=True,
    locale="en-US",
):
    """Run the research agent with the given question.

    Args:
        question: The research query or objective
        debug: If True, enables debug level logging
        max_research_iterations: Maximum number of research iterations
        enable_background_investigation: If True, performs background investigation before planning
        auto_execute: If True, automatically executes the research plan
        locale: Language locale for the research
    """
    asyncio.run(
        run_research_agent_async(
            user_input=question,
            debug=debug,
            max_research_iterations=max_research_iterations,
            enable_background_investigation=enable_background_investigation,
            auto_execute=auto_execute,
            locale=locale,
        )
    )


def main(
    debug=False,
    max_research_iterations=3,
    enable_background_investigation=True,
    auto_execute=True,
):
    """Interactive mode with built-in questions.

    Args:
        debug: If True, enables debug level logging
        max_research_iterations: Maximum number of research iterations
        enable_background_investigation: If True, performs background investigation before planning
        auto_execute: If True, automatically executes the research plan
    """
    # First select language
    language = inquirer.select(
        message="Select language / 选择语言:",
        choices=["English", "中文"],
    ).execute()

    # Choose questions based on language
    questions = (
        BUILT_IN_QUESTIONS if language == "English" else BUILT_IN_QUESTIONS_ZH_CN
    )
    ask_own_option = (
        "[Ask my own question]" if language == "English" else "[自定义问题]"
    )

    # Select a question
    initial_question = inquirer.select(
        message=(
            "What do you want to know?" if language == "English" else "您想了解什么?"
        ),
        choices=[ask_own_option] + questions,
    ).execute()

    if initial_question == ask_own_option:
        initial_question = inquirer.text(
            message=(
                "What do you want to know?"
                if language == "English"
                else "您想了解什么?"
            ),
        ).execute()

    # Determine locale from language selection
    locale = "zh-CN" if language == "中文" else "en-US"

    # Pass all parameters to ask function
    ask(
        question=initial_question,
        debug=debug,
        max_research_iterations=max_research_iterations,
        enable_background_investigation=enable_background_investigation,
        auto_execute=auto_execute,
        locale=locale,
    )


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run the Deer")
    parser.add_argument("query", nargs="*", help="The query to process")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode with built-in questions",
    )
    parser.add_argument(
        "--max-research-iterations",
        type=int,
        default=3,
        help="Maximum number of research iterations (default: 3)",
    )
    parser.add_argument(
        "--locale",
        type=str,
        default="en-US",
        help="Language locale (default: en-US)",
    )
    parser.add_argument(
        "--no-auto-execute",
        action="store_false",
        dest="auto_execute",
        help="Disable automatic execution of research plan",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--no-background-investigation",
        action="store_false",
        dest="enable_background_investigation",
        help="Disable background investigation before planning",
    )

    args = parser.parse_args()

    if args.interactive:
        # Pass command line arguments to main function
        main(
            debug=args.debug,
            max_research_iterations=args.max_research_iterations,
            enable_background_investigation=args.enable_background_investigation,
            auto_execute=args.auto_execute,
        )
    else:
        # Parse user input from command line arguments or user input
        if args.query:
            user_query = " ".join(args.query)
        else:
            user_query = input("Enter your research query: ")

        # Run the research agent with the provided parameters
        ask(
            question=user_query,
            debug=args.debug,
            max_research_iterations=args.max_research_iterations,
            enable_background_investigation=args.enable_background_investigation,
            auto_execute=args.auto_execute,
            locale=args.locale,
        )
