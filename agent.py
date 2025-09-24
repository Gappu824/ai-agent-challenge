#!/usr/bin/env python3
"""
Agent-as-Coder: An autonomous AI agent that generates, tests, and refines
bank statement parsers from PDF documents.

This agent employs a state-driven graph architecture to manage a robust
plan -> code -> test -> self-correct loop, ensuring the final generated
parser meets all specified quality and correctness criteria.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import pandas as pd
from typing import TypedDict, Optional, Annotated

# LangGraph provides a robust framework for building stateful, multi-step agent applications.
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Gemini is used for its advanced reasoning and code generation capabilities.
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- State Management ---
class AgentState(TypedDict):
    """
    Represents the state of the agent's workflow. This state is passed between
    nodes and updated at each step, creating a traceable execution history.
    """
    messages: Annotated[list, add_messages]
    target_bank: str
    parser_path: str
    csv_path: str
    current_code: Optional[str]
    test_results: Optional[str]
    attempt_count: int
    max_attempts: int
    task_complete: bool

class BankStatementParserAgent:
    """
    An autonomous agent designed to generate and validate bank statement parsers.
    It orchestrates a cycle of code generation and testing until a correct
    and robust parser is created.
    """

    def __init__(self, api_key: str):
        """
        Initializes the agent, configures the Gemini model, and builds the
        workflow graph that defines the agent's behavior.
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            'gemini-1.5-pro',
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Constructs the agent's execution graph using LangGraph. This graph
        defines the nodes (steps) and edges (transitions) of the workflow,
        creating a clear and maintainable architecture.
        """
        workflow = StateGraph(AgentState)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("generate_code", self._generate_code_node)
        workflow.add_node("run_tests", self._run_tests_node)
        workflow.add_node("self_fix", self._self_fix_node)

        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "generate_code")
        workflow.add_conditional_edges("generate_code", self._should_test, {"test": "run_tests", "end": END})
        workflow.add_conditional_edges("run_tests", self._should_continue_fixing, {"fix": "self_fix", "end": END})
        workflow.add_edge("self_fix", "generate_code")
        
        return workflow.compile()

    # --- Graph Nodes ---

    def _plan_node(self, state: AgentState) -> AgentState:
        print(f"📋 Planning parser for {state['target_bank']}...")
        state['messages'].append({'role': 'user', 'content': f"Plan a Python parser for {state['target_bank']}."})
        return state

    def _generate_code_node(self, state: AgentState) -> AgentState:
        print(f"🔧 Generating parser code (Attempt {state['attempt_count']})...")
        csv_schema = pd.read_csv(state['csv_path']).columns.tolist()
        
        prompt = f"""
        You are an expert Python developer. Generate a parser for '{state['target_bank']}' bank statements.

        **CRITICAL INSTRUCTIONS:**
        1.  The PDF data has exactly 5 columns. Your parser must extract and handle exactly 5 columns.
        2.  The required output DataFrame columns are STRICTLY: `['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']`.
        3.  **DO NOT HALLUCINATE OR ADD EXTRA COLUMNS.** Specifically, do not add a 'Chq./Ref.No.' column. This is the most common cause of failure.
        4.  Use `pdfplumber` and `page.extract_tables()`.
        5.  Create the DataFrame from a list of dictionaries to ensure column mapping is correct.

        **Feedback from previous attempt:** {state.get('test_results', 'This is the first attempt.')}

        Provide only the complete, runnable Python code.
        """
        
        try:
            response = self.model.generate_content(prompt)
            code = self._extract_code(response.text)
            
            if code:
                os.makedirs(os.path.dirname(state['parser_path']), exist_ok=True)
                with open(state['parser_path'], 'w') as f:
                    f.write(code)
                state['current_code'] = code
            else:
                state['current_code'] = None
                state['test_results'] = "Failed to generate valid Python code."
        except Exception as e:
            state['current_code'] = None
            state['test_results'] = f"An exception occurred during code generation: {e}"

        return state

    def _run_tests_node(self, state: AgentState) -> AgentState:
        print("🧪 Running tests...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "test_parser.py"],
                capture_output=True, text=True, cwd=Path.cwd(), timeout=60
            )
            if result.returncode == 0:
                state['test_results'] = "All tests passed successfully."
                state['task_complete'] = True
            else:
                state['test_results'] = f"Tests failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                state['task_complete'] = False
        except Exception as e:
            state['test_results'] = f"An unexpected error occurred while running tests: {e}"
            state['task_complete'] = False
        return state

    def _self_fix_node(self, state: AgentState) -> AgentState:
        print("🔄 Self-correcting based on test feedback...")
        state['attempt_count'] += 1
        return state

    # --- Conditional Logic & Utilities ---

    def _should_test(self, state: AgentState) -> str:
        return "test" if state.get('current_code') else "end"

    def _should_continue_fixing(self, state: AgentState) -> str:
        if state['task_complete']:
            return "end"
        return "fix" if state['attempt_count'] < state['max_attempts'] else "end"

    @staticmethod
    def _extract_code(text: str) -> Optional[str]:
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        return text.strip() if text else None

    # --- Public API ---

    def run(self, target_bank: str, max_attempts: int = 3):
        print(f"🚀 Starting agent for {target_bank} parser...")
        
        initial_state = AgentState(
            messages=[],
            target_bank=target_bank,
            parser_path=str(Path.cwd() / "custom_parsers" / f"{target_bank}_parser.py"),
            csv_path=str(Path.cwd() / "data" / target_bank / f"{target_bank}_sample.csv"),
            attempt_count=1,
            max_attempts=max_attempts,
            task_complete=False,
            current_code=None,
            test_results=None,
        )

        final_state = self.workflow.invoke(initial_state)

        if final_state['task_complete']:
            print(f"✅ Successfully generated and tested parser: {final_state['parser_path']}")
        else:
            print(f"❌ Failed to generate a working parser after {final_state['attempt_count']} attempts.")
            print(f"Last test result:\n{final_state['test_results']}")

def main():
    parser = argparse.ArgumentParser(description="AI Agent for Bank Statement Parser Generation.")
    parser.add_argument("--target", required=True, help="Target bank (e.g., 'icici').")
    parser.add_argument("--api-key", required=True, help="Google Gemini API key.")
    args = parser.parse_args()

    agent = BankStatementParserAgent(api_key=args.api_key)
    agent.run(target_bank=args.target)

if __name__ == "__main__":
    main()