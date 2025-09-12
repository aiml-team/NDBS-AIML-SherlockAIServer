import os
import json
import re
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class JSONContentSummarizer:
    def __init__(self):
        """Initialize the summarizer with Azure OpenAI configuration from environment variables"""
        
        # Load configuration from environment variables
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
        api_type = os.getenv("AZURE_OPENAI_API_TYPE", "azure")
        
        # Validate required environment variables
        if not all([endpoint, deployment, subscription_key, api_version]):
            missing_vars = []
            if not endpoint: missing_vars.append("AZURE_OPENAI_ENDPOINT")
            if not deployment: missing_vars.append("AZURE_OPENAI_DEPLOYMENT")
            if not subscription_key: missing_vars.append("AZURE_OPENAI_API_KEY")
            if not api_version: missing_vars.append("OPENAI_API_VERSION")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please set these environment variables.")
        
        # Set up Azure OpenAI environment variables
        os.environ["AZURE_OPENAI_ENDPOINT"] = endpoint
        os.environ["AZURE_OPENAI_API_KEY"] = subscription_key
        os.environ["AZURE_OPENAI_API_VERSION"] = api_version
        os.environ["OPENAI_API_VERSION"] = api_version
        os.environ["AZURE_OPENAI_API_TYPE"] = api_type
        
        print("Environment variables loaded successfully!")
        
        # Initialize LangChain Azure ChatOpenAI
        self.llm = AzureChatOpenAI(
            deployment_name=deployment,
            api_version=api_version,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Create prompt template for summarization
        self.prompt_template = PromptTemplate(
            input_variables=["content_text"],
            template="""You are a professional business analyst. Summarize the following content in clear, professional English.

CRITICAL REQUIREMENTS:
1. Maintain ALL image references (like [IMAGE_1], [IMAGE_2], etc.) in their EXACT original positions
2. Provide a concise but comprehensive professional summary
3. Preserve all key business information and technical details
4. Use proper business terminology and professional language
5. Do NOT add any extra words, explanations, or commentary beyond the summarized content
6. Return ONLY the summarized text, nothing else

Content to summarize:
{content_text}

Summarized content:"""
        )
        
        # Create the chain using modern LangChain syntax
        self.summarization_chain = self.prompt_template | self.llm
    
    def extract_image_references(self, text: str) -> List[str]:
        """Extract all image references from text"""
        return re.findall(r'\[IMAGE_\d+\]', text)
    
    def ensure_image_references_preserved(self, original_text: str, summarized_text: str) -> str:
        """Ensure ONLY the image references from original text are present in summarized text"""
        original_images = self.extract_image_references(original_text)
        
        # Remove any existing image references from summarized text first
        cleaned_summarized = re.sub(r'\[IMAGE_\d+\]', '', summarized_text).strip()
        
        # Add back only the images that were in the original text
        if original_images:
            # Find the best position to insert image references
            result_text = cleaned_summarized
            for image_ref in original_images:
                result_text = result_text.rstrip() + f" {image_ref}"
            return result_text
        else:
            return cleaned_summarized
    
    def normalize_text(self, text: str) -> str:
        """Normalize Unicode characters to ASCII equivalents"""
        # Replace curly quotes with straight quotes
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('\u2018', "'")
        text = text.replace('\u2019', "'")
        text = text.replace('\u2013', '-')
        text = text.replace('\u2014', '--')
        text = text.replace('\u2026', '...')
        
        return text
    
    def summarize_content(self, content_text: str) -> str:
        """Summarize a single content text while preserving image references"""
        try:
            print(f"Processing content: {content_text[:100]}...")
            
            # Normalize Unicode characters first
            normalized_text = self.normalize_text(content_text)
            
            # Check what image references are in the original
            original_images = self.extract_image_references(normalized_text)
            print(f"Found images in original: {original_images}")
            
            # Run the summarization chain
            result = self.summarization_chain.invoke({"content_text": normalized_text})
            
            # Extract content from the AI message
            if hasattr(result, 'content'):
                summarized_text = result.content
            else:
                summarized_text = str(result)
            
            print(f"AI summarized to: {summarized_text[:100]}...")
            
            # Ensure ONLY original image references are preserved
            summarized = self.ensure_image_references_preserved(normalized_text, summarized_text)
            
            # Normalize the output as well
            summarized = self.normalize_text(summarized)
            
            final_images = self.extract_image_references(summarized)
            print(f"Final images in output: {final_images}")
            print(f"Final summarized content: {summarized[:150]}...")
            print("-" * 80)
            
            return summarized
            
        except Exception as e:
            print(f"Error summarizing content: {e}")
            return self.normalize_text(content_text)
    
    def process_json_recursively(self, data: Any, path: str = "") -> Any:
        """Recursively process JSON structure to find and summarize content"""
        if isinstance(data, dict):
            processed_dict = {}
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if key == 'content' and isinstance(value, str):
                    print(f"Found content field at: {current_path}")
                    # This is a content field - summarize it
                    processed_dict[key] = self.summarize_content(value)
                elif isinstance(value, str):
                    # Normalize other string values but don't summarize
                    processed_dict[self.normalize_text(key)] = self.normalize_text(value)
                else:
                    # Recursively process other fields
                    processed_key = self.normalize_text(key) if isinstance(key, str) else key
                    processed_dict[processed_key] = self.process_json_recursively(value, current_path)
            return processed_dict
        
        elif isinstance(data, list):
            return [self.process_json_recursively(item, f"{path}[{i}]") for i, item in enumerate(data)]
        
        elif isinstance(data, str):
            return self.normalize_text(data)
        
        else:
            return data
    
    def summarize_json(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to summarize JSON content"""
        print("Starting JSON summarization process...")
        print("=" * 80)
        
        result = self.process_json_recursively(input_data)
        
        print("=" * 80)
        print("JSON summarization completed!")
        return result

def process_json_file(file_path: str, output_path: str = None):
    """Process JSON from file"""
    
    try:
        summarizer = JSONContentSummarizer()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return None
    
    try:
        # Load JSON from file
        with open(file_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Process the JSON
        summarized_data = summarizer.summarize_json(input_data)
        
        # Determine output path
        if output_path is None:
            output_path = file_path.replace('.json', '_summarized.json')
        
        # Save summarized JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summarized_data, f, indent=2, ensure_ascii=False)
        
        print(f"Summarized JSON saved to: {output_path}")
        return summarized_data
        
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    test_data = {
        'Record to Report (R2R)': {
            'General Notes & "Wish List"': {
                'content': 'What are your key goals/objectives from a finance standpoint for this organization? Primary mission is growth – expansion in US and Canada Reduce claims, reduce costs Speeding up close – currently takes about a month Lots of manual checklists across various users [IMAGE_1] Pull reports from system rather than excel processing',
                'images': {'IMAGE_1': '/9j//2Q=='}
            }
        }
    }
    
    try:
        summarizer = JSONContentSummarizer()
        result = summarizer.summarize_json(test_data)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")