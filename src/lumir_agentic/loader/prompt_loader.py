import os 
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Dict, Any, Optional

class PromptLoader:
    """Utility class for loading and rendering Jinja2 prompt templates"""
    
    def __init__(self, template_dir:str = None):
        """
        Initialize the PromptLoader with the directory containing templates.
        """

        if template_dir is None:
            current_dir = Path(__file__).parent
            template_dir = current_dir / "prompt"   

        self.template_dir = Path(template_dir)

        # Ensure template directory exists
        if not self.template_dir.exists() or not self.template_dir.is_dir():
            raise FileNotFoundError(f"Template directory {self.template_dir} does not exist or is not a directory.")
        
        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
      
    def load_template(self, template_name: str) -> Template:
        """
        Load a Jinja2 template by name

        Args:
            template_name: Name of the template file (with or without .j2 extension)

        Returns:
            Jinja2 Template object
        """
        # Add .j2 extension if not present
        if not template_name.endswith('.j2'):
            template_name += '.j2'
        
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            raise FileNotFoundError(f"Template '{template_name}' not found in {self.template_dir}: {e}")
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """
        Load and render a template with given variables
        
        Args:
            template_name: Name of the template file
            **kwargs: Variables to pass to the template
            
        Returns:
            Rendered template as string
        """
        template = self.load_template(template_name)
        return template.render(**kwargs)
    
    def list_templates(self) -> list:
        """
        List all available templates in the template directory
        
        Returns:
            List of template filenames
        """
        return [f.name for f in self.template_dir.glob("*.j2")]
    

# if __name__ == "__main__":

#     loader = PromptLoader(template_dir="./core/prompt")
#     print("Available templates:", loader.list_templates())
#     rendered = loader.render_template(template_name="plan", reasoning_result="This is a test reasoning result", user_profile="User profile data"
#     )
#     print("Rendered Template:\n", rendered)
