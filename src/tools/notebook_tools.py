# SPDX-License-Identifier: MIT

"""
Jupyter notebook tools for reading and editing notebook files.
"""

import json
import os
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool


def _load_notebook(notebook_path: str) -> Dict[str, Any]:
    """Load a Jupyter notebook from file."""
    if not os.path.isabs(notebook_path):
        raise ValueError(f"notebook_path must be an absolute path, got: {notebook_path}")
    
    if not os.path.exists(notebook_path):
        raise FileNotFoundError(f"Notebook file does not exist: {notebook_path}")
    
    if not notebook_path.endswith('.ipynb'):
        raise ValueError(f"File must be a Jupyter notebook (.ipynb), got: {notebook_path}")
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    return notebook


def _save_notebook(notebook_path: str, notebook: Dict[str, Any]) -> None:
    """Save a Jupyter notebook to file."""
    with open(notebook_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)


def _format_cell_output(cell: Dict[str, Any], cell_num: int) -> str:
    """Format a single cell for display."""
    cell_type = cell.get('cell_type', 'unknown')
    source = cell.get('source', [])
    
    # Convert source to string
    if isinstance(source, list):
        source_text = ''.join(source)
    else:
        source_text = str(source)
    
    result = f"=== Cell {cell_num} ({cell_type}) ===\n"
    result += f"Source:\n{source_text}\n"
    
    # Add execution count for code cells
    if cell_type == 'code':
        execution_count = cell.get('execution_count')
        if execution_count is not None:
            result += f"Execution count: {execution_count}\n"
    
    # Add outputs for code cells
    outputs = cell.get('outputs', [])
    if outputs:
        result += "Outputs:\n"
        for i, output in enumerate(outputs):
            output_type = output.get('output_type', 'unknown')
            result += f"  Output {i+1} ({output_type}):\n"
            
            # Handle different output types
            if output_type == 'stream':
                text = output.get('text', [])
                if isinstance(text, list):
                    text = ''.join(text)
                result += f"    {text}\n"
            elif output_type in ['execute_result', 'display_data']:
                data = output.get('data', {})
                for mime_type, content in data.items():
                    if mime_type == 'text/plain':
                        if isinstance(content, list):
                            content = ''.join(content)
                        result += f"    {content}\n"
                    else:
                        result += f"    [{mime_type} content]\n"
            elif output_type == 'error':
                traceback = output.get('traceback', [])
                if isinstance(traceback, list):
                    traceback = '\n'.join(traceback)
                result += f"    Error: {traceback}\n"
    
    result += "\n"
    return result


@tool
def notebook_read(notebook_path: str) -> str:
    """
    Reads a Jupyter notebook (.ipynb file) and returns all of the cells with their outputs. 
    Jupyter notebooks are interactive documents that combine code, text, and visualizations, 
    commonly used for data analysis and scientific computing. The notebook_path parameter 
    must be an absolute path, not a relative path.

    Args:
        notebook_path: The absolute path to the Jupyter notebook file to read (must be absolute, not relative)

    Returns:
        Formatted string containing all notebook cells and their outputs
    """
    try:
        notebook = _load_notebook(notebook_path)
        
        # Get basic notebook info
        metadata = notebook.get('metadata', {})
        kernel_info = metadata.get('kernelspec', {})
        kernel_name = kernel_info.get('display_name', 'Unknown')
        
        result = f"Jupyter Notebook: {notebook_path}\n"
        result += f"Kernel: {kernel_name}\n"
        result += f"Number of cells: {len(notebook.get('cells', []))}\n\n"
        
        # Process each cell
        cells = notebook.get('cells', [])
        for i, cell in enumerate(cells):
            result += _format_cell_output(cell, i)
        
        return result
        
    except Exception as e:
        return f"Error reading notebook: {str(e)}"


@tool
def notebook_edit_cell(
    notebook_path: str,
    cell_number: int,
    new_source: str,
    cell_type: Optional[str] = None,
    edit_mode: str = "replace"
) -> str:
    """
    Completely replaces the contents of a specific cell in a Jupyter notebook (.ipynb file) with new source. 
    Jupyter notebooks are interactive documents that combine code, text, and visualizations, commonly used 
    for data analysis and scientific computing. The notebook_path parameter must be an absolute path, not 
    a relative path. The cell_number is 0-indexed. Use edit_mode=insert to add a new cell at the index 
    specified by cell_number. Use edit_mode=delete to delete the cell at the index specified by cell_number.

    Args:
        notebook_path: The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)
        cell_number: The index of the cell to edit (0-based)
        new_source: The new source for the cell
        cell_type: The type of the cell (code or markdown). If not specified, it defaults to the current cell type. 
                  If using edit_mode=insert, this is required
        edit_mode: The type of edit to make (replace, insert, delete). Defaults to replace

    Returns:
        Confirmation message or error description
    """
    try:
        notebook = _load_notebook(notebook_path)
        cells = notebook.get('cells', [])
        
        if edit_mode == "delete":
            # Delete cell
            if cell_number < 0 or cell_number >= len(cells):
                return f"Error: Cell number {cell_number} is out of range (0-{len(cells)-1})"
            
            deleted_cell = cells.pop(cell_number)
            cell_type_deleted = deleted_cell.get('cell_type', 'unknown')
            
            _save_notebook(notebook_path, notebook)
            return f"Successfully deleted cell {cell_number} ({cell_type_deleted}) from {notebook_path}"
        
        elif edit_mode == "insert":
            # Insert new cell
            if cell_type is None:
                return "Error: cell_type is required when using edit_mode=insert"
            
            if cell_type not in ['code', 'markdown']:
                return f"Error: cell_type must be 'code' or 'markdown', got: {cell_type}"
            
            if cell_number < 0 or cell_number > len(cells):
                return f"Error: Cell number {cell_number} is out of range for insertion (0-{len(cells)})"
            
            # Create new cell
            new_cell = {
                "cell_type": cell_type,
                "metadata": {},
                "source": new_source.split('\n') if '\n' in new_source else [new_source]
            }
            
            if cell_type == 'code':
                new_cell["execution_count"] = None
                new_cell["outputs"] = []
            
            # Insert at specified position
            cells.insert(cell_number, new_cell)
            
            _save_notebook(notebook_path, notebook)
            return f"Successfully inserted new {cell_type} cell at position {cell_number} in {notebook_path}"
        
        else:  # replace mode (default)
            # Replace cell content
            if cell_number < 0 or cell_number >= len(cells):
                return f"Error: Cell number {cell_number} is out of range (0-{len(cells)-1})"
            
            cell = cells[cell_number]
            old_type = cell.get('cell_type', 'code')
            
            # Use provided cell_type or keep existing
            target_type = cell_type if cell_type else old_type
            
            if target_type not in ['code', 'markdown']:
                return f"Error: cell_type must be 'code' or 'markdown', got: {target_type}"
            
            # Update cell content
            cell['cell_type'] = target_type
            cell['source'] = new_source.split('\n') if '\n' in new_source else [new_source]
            
            # Reset execution-related fields for code cells
            if target_type == 'code':
                cell['execution_count'] = None
                cell['outputs'] = []
            else:
                # Remove code-specific fields for markdown cells
                cell.pop('execution_count', None)
                cell.pop('outputs', None)
            
            _save_notebook(notebook_path, notebook)
            return f"Successfully replaced cell {cell_number} ({target_type}) in {notebook_path}"
        
    except Exception as e:
        return f"Error editing notebook: {str(e)}" 