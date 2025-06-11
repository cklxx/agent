# SPDX-License-Identifier: MIT

"""
Writing Task Planner module for handling creative writing tasks with planning capabilities.
"""

import logging
import json
from typing import List, Dict, Any, Optional

from src.llms.llm import get_llm_by_type
# Assuming apply_prompt_template is in src.prompts or src.prompts.template
# Adjust the import based on its actual location if different.
from src.prompts.template import apply_prompt_template

# Setup loggers
logger = logging.getLogger(__name__)
writing_task_planner_llm_logger = logging.getLogger("writing_task_planner_llm_logger")


class WritingTaskPlanner:
    """Handles the planning and breakdown of creative writing tasks."""

    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self.current_step_index: int = 0
        logger.info("Writing Task Planner initialized")

    def plan_task(self, description: str) -> List[Dict[str, Any]]:
        """
        Breaks down a complex creative writing task into executable steps.

        Args:
            description: The description of the writing task.

        Returns:
            A list of task steps with details.
        """
        writing_task_planner_llm_logger.info(
            f"🚀 Starting writing task planning for: {description[:100]}{'...' if len(description) > 100 else ''}"
        )
        logger.info(
            f"📋 Planning creative writing task: {description[:50]}{'...' if len(description) > 50 else ''}"
        )

        # Generate an execution plan based on the task description
        plan = self._analyze_task(description)
        self.tasks = plan

        logger.info(f"✅ Writing task planning complete, generated {len(plan)} steps.")

        # Log detailed steps only in debug mode
        for i, step in enumerate(plan, 1):
            logger.debug(f"  Step {i}: [{step.get('type', 'general')}] {step.get('title', 'Untitled Step')} - {step.get('description', 'No description')[:60]}...")

        return plan

    def _analyze_task(self, description: str) -> List[Dict[str, Any]]:
        """Analyzes the writing task and generates a detailed execution plan."""
        logger.debug("Starting LLM analysis for writing task...")

        try:
            llm = get_llm_by_type("reasoning") # Use a reasoning model for better planning
            writing_task_planner_llm_logger.info("🧠 LLM analysis in progress for writing task...")

            prompt_state = {"messages": [], "task_description": description}
            messages = apply_prompt_template("writing/writing_task_planner_prompt", prompt_state)

            response = llm.invoke(messages)
            llm_response_content = response.content if hasattr(response, "content") else str(response)

            try:
                # Clean up potential markdown formatting around JSON
                clean_response = llm_response_content.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                clean_response = clean_response.strip()

                plan_data = json.loads(clean_response)

                if "phases" not in plan_data or not isinstance(plan_data["phases"], list):
                    raise ValueError("Plan data is missing 'phases' list or it's malformed.")

                writing_task_planner_llm_logger.info(f"📝 LLM generated {len(plan_data['phases'])} execution phases.")

                converted_steps: List[Dict[str, Any]] = []
                step_counter = 1
                for phase_item in plan_data["phases"]:
                    phase_name = phase_item.get("name", "Unknown Phase")
                    phase_desc = phase_item.get("description", "No phase description.")

                    if not isinstance(phase_item.get("steps"), list):
                        logger.warning(f"Phase '{phase_name}' has malformed steps. Skipping.")
                        continue

                    for step_item in phase_item["steps"]:
                        converted_step = {
                            "id": step_item.get("id", f"step_{step_counter}"),
                            "phase": phase_name,
                            "phase_description": phase_desc,
                            "type": step_item.get("type", "general_writing_task"),
                            "title": step_item.get("title", "Untitled Step"),
                            "description": step_item.get("description", "No step description."),
                            "estimated_creativity_level": step_item.get("estimated_creativity_level", "medium"),
                            # Add any other relevant fields from your prompt's expected output
                        }
                        converted_steps.append(converted_step)
                        step_counter += 1

                writing_task_planner_llm_logger.info(f"✅ Successfully parsed LLM plan: {len(converted_steps)} total steps.")
                logger.debug(f"Generated plan details: {json.dumps(converted_steps, indent=2)}")
                return converted_steps

            except (json.JSONDecodeError, ValueError) as e:
                writing_task_planner_llm_logger.warning(f"LLM plan parsing failed: {str(e)}. Raw response: {llm_response_content[:500]}")
                logger.debug(f"LLM plan parsing error: {e}. Raw response: {llm_response_content}")

        except Exception as e:
            writing_task_planner_llm_logger.error(f"LLM task analysis failed: {str(e)}")
            logger.debug(f"LLM analysis error: {e}")

        # Fallback to a predefined plan structure for writing tasks
        writing_task_planner_llm_logger.info("🔄 Reverting to fallback plan for writing task.")
        logger.info("Using fallback plan structure for writing task.")

        fallback_plan = [
            {
                "id": "fallback_step_1",
                "phase": "inspiration_gathering",
                "phase_description": "Gather initial thoughts and analyze the core request.",
                "type": "analyze_request",
                "title": "Analyze User Request for Key Themes",
                "description": f"Carefully review the user's request ('{description[:100]}...') to identify main themes, desired tone, genre, and any specific elements mentioned."
            },
            {
                "id": "fallback_step_2",
                "phase": "inspiration_gathering",
                "phase_description": "Gather initial thoughts and analyze the core request.",
                "type": "generate_broad_ideas",
                "title": "Generate 2-3 Initial Broad Ideas",
                "description": "Based on the analysis, brainstorm 2-3 distinct high-level concepts or directions for the creative piece."
            },
            {
                "id": "fallback_step_3",
                "phase": "content_development",
                "phase_description": "Develop chosen ideas into more concrete elements.",
                "type": "develop_chosen_idea",
                "title": "Develop One Chosen Idea Further",
                "description": "Select one of the broad ideas and elaborate on it, adding more specific details or a central premise."
            },
            {
                "id": "fallback_step_4",
                "phase": "content_development",
                "phase_description": "Develop chosen ideas into more concrete elements.",
                "type": "generate_character_concepts",
                "title": "Generate Character Concepts (if applicable)",
                "description": "If relevant to the idea, brainstorm 1-2 simple character concepts including a name and a key trait."
            },
            {
                "id": "fallback_step_5",
                "phase": "content_development",
                "phase_description": "Develop chosen ideas into more concrete elements.",
                "type": "suggest_plot_points",
                "title": "Suggest Plot Points or Narrative Snippets (if applicable)",
                "description": "If story-based, suggest 2-3 basic plot points (beginning, middle, end) or short narrative snippets."
            },
            {
                "id": "fallback_step_6",
                "phase": "refinement_suggestions",
                "phase_description": "Suggest ways to enhance and refine the generated content.",
                "type": "suggest_uniqueness",
                "title": "Suggest Ways to Make the Idea More Unique",
                "description": "Propose 1-2 ways to add a unique twist or perspective to the developed idea."
            },
            {
                "id": "fallback_step_7",
                "phase": "refinement_suggestions",
                "phase_description": "Suggest ways to enhance and refine the generated content.",
                "type": "propose_alternatives",
                "title": "Propose Alternative Viewpoints or Styles",
                "description": "Briefly suggest an alternative approach, viewpoint, or stylistic choice for the creative piece."
            }
        ]
        return fallback_plan

    def get_next_step(self) -> Optional[Dict[str, Any]]:
        """Gets the next step in the planned task list."""
        if self.current_step_index < len(self.tasks):
            step = self.tasks[self.current_step_index]
            logger.info(
                f"Getting step {self.current_step_index + 1}/{len(self.tasks)}: [{step.get('type', 'general')}] {step.get('title', 'Untitled Step')}"
            )
            self.current_step_index += 1
            return step
        logger.info("All writing task steps have been processed.")
        return None

    def mark_step_completed(self, step_id: str, result: Any):
        """Marks a specific step as completed and stores its result."""
        # In this version, step_id is a string like "fallback_step_1" or "step_1"
        for step in self.tasks:
            if step.get("id") == step_id:
                step["completed"] = True
                step["result"] = result
                logger.info(f"Step '{step_id}' ({step.get('title', '')}) marked as completed.")
                return
        logger.warning(f"Attempted to mark non-existent step '{step_id}' as completed.")

# Example usage (for local testing)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    planner = WritingTaskPlanner()

    # Test with a simple description that might use the LLM
    # (Requires LLM and prompt setup to run fully)
    # test_description_llm = "I want to write a short fantasy story about a lost magical artifact."
    # print(f"\n--- Planning for: '{test_description_llm}' (LLM attempt) ---")
    # plan_llm = planner.plan_task(test_description_llm)
    # for s in plan_llm:
    #     print(f"ID: {s['id']}, Phase: {s['phase']}, Title: {s['title']}, Desc: {s['description'][:60]}...")

    # Test fallback (by simulating LLM failure or providing an empty/error-prone description)
    # To force fallback for testing, you might temporarily sabotage the _analyze_task's try block
    test_description_fallback = "Need ideas for a poem about the sea."
    print(f"\n--- Planning for: '{test_description_fallback}' (likely Fallback) ---")
    plan_fallback = planner.plan_task(test_description_fallback)
    for s in plan_fallback:
         print(f"ID: {s['id']}, Phase: {s['phase']}, Title: {s['title']}, Desc: {s['description'][:60]}...")

    print("\n--- Getting next steps (Fallback example) ---")
    next_s = planner.get_next_step()
    while next_s:
        print(f"Executing: {next_s['title']}")
        planner.mark_step_completed(next_s['id'], "Mock result for " + next_s['title'])
        next_s = planner.get_next_step()

```
