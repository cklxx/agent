#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path


class ColorPrint:
    """Color terminal output class"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'

    @staticmethod
    def blue(text):
        return f"{ColorPrint.BLUE}{text}{ColorPrint.ENDC}"

    @staticmethod
    def green(text):
        return f"{ColorPrint.GREEN}{text}{ColorPrint.ENDC}"

    @staticmethod
    def yellow(text):
        return f"{ColorPrint.YELLOW}{text}{ColorPrint.ENDC}"

    @staticmethod
    def red(text):
        return f"{ColorPrint.RED}{text}{ColorPrint.ENDC}"


class SimpleRunner:
    """Simplified runner, only runs the main program"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        
        # Predefined question list
        self.questions = [
            "3-day travel plan for Haikou, staying at Sheraton Hotel",
            "Write a Python function to calculate Fibonacci sequence",
            "Recommend 5 science fiction novels",
            "Explain the basic principles of quantum mechanics",
            "How to make braised pork (Hong Shao Rou)?"
        ]
    
    def print_header(self):
        """Print header"""
        print(f"{ColorPrint.blue('=' * 40)}")
        print(f"{ColorPrint.blue('      Agent Project Simple Runner       ')}")
        print(f"{ColorPrint.blue('=' * 40)}")
        print(f"{ColorPrint.blue('[*] Preparing environment...')}")
        print(f"{ColorPrint.blue('[*] Starting main application...')}")
        print(f"{ColorPrint.yellow('[!] Note: This script does not start any MCP services, please ensure required services are started manually')}")
        print(f"{ColorPrint.blue('=' * 40)}")
    
    def select_question(self):
        """Let user select a question"""
        print(f"{ColorPrint.blue('Available questions:')}")
        for i, question in enumerate(self.questions, 1):
            print(f"{ColorPrint.green(f'{i}.')} {question}")
        
        print(f"{ColorPrint.blue('-' * 40)}")
        print(f"{ColorPrint.yellow(f'Please select a question number (1-{len(self.questions)}), or enter 0 for custom question:')}")
        
        try:
            choice = int(input("> "))
            if choice == 0:
                print(f"{ColorPrint.yellow('Please enter your question:')}")
                custom_question = input("> ")
                return custom_question
            elif 1 <= choice <= len(self.questions):
                return self.questions[choice-1]
            else:
                print(f"{ColorPrint.red('[!] Invalid selection, will use default question')}")
                return self.questions[0]
        except ValueError:
            print(f"{ColorPrint.red('[!] Invalid input, will use default question')}")
            return self.questions[0]
    
    def run_main_app(self, question):
        """Run main application with the question"""
        print(f"{ColorPrint.blue('[*] Using question:')} {ColorPrint.green(question)}")
        print(f"{ColorPrint.blue('[*] Starting execution...')}")
        
        try:
            # Create a pipe to pass the question to the main program
            process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdin=subprocess.PIPE,
                text=True
            )
            
            # Send question to program's standard input
            process.communicate(input=question)
            
            return process.returncode == 0
        except Exception as e:
            print(f"{ColorPrint.red(f'[!] Error running main program: {e}')}")
            return False
    
    def run(self):
        """Run main process"""
        self.print_header()
        question = self.select_question()
        self.run_main_app(question)


if __name__ == "__main__":
    runner = SimpleRunner()
    runner.run() 