def parse_document_sections(sections_list, json_data):
    """
    Parse document sections into nested dictionary structure:
    {
        "Main Section": {
            "Subsection 1": {"content": "...", "images": {...}},
            "Subsection 2": {"content": "...", "images": {...}},
            ...
        }
    }
    """
    
    # Define main section headers
    main_sections = [
        "General Business Overview",
        "Idea to Market", 
        "Source to Pay (S2P)",
        "Plan to Produce (P2P)",
        "Detect to Correct (D2C)",
        "Forecast to Fulfill (F2F)", 
        "Warehouse Execution (WM / EWM)",
        "Lead to Cash (L2C)",
        "Logistics Planning & Transportation (TM)",
        "Request to Service (R2S)",
        "Record to Report (R2R)",
        "Acquire to Dispose (A2D)",
        "Environmental, Social, and Governance (ESG) Processes",
        "Hire to Retire (H2R)",
        "Enterprise Reporting; Data & Analytics Strategy",
        "Other Workstream(s)"
    ]
    
    # Validate input data
    if not json_data or 'sequence' not in json_data:
        print("Error: Invalid JSON data structure. Expected 'sequence' key.")
        return {}
    
    if not isinstance(json_data['sequence'], list) or len(json_data['sequence']) == 0:
        print("Error: 'sequence' must be a non-empty list.")
        return {}
    
    # Create sections_set for faster lookup
    sections_set = set(sections_list)
    main_sections_set = set(main_sections)
    
    dic = {}
    img_count = 1
    current_main_section = None
    current_subsection = None
    
    print(f"Processing {len(json_data['sequence'])} sequence items...")
    
    # Process each item in the sequence (skip the header table)
    for i in range(1, len(json_data['sequence'])):
        seq_item = json_data['sequence'][i]
        
        if not isinstance(seq_item, dict) or 'content' not in seq_item or 'type' not in seq_item:
            print(f"Warning: Skipping invalid sequence item at index {i}")
            continue
            
        seq_content = seq_item['content']
        seq_type = seq_item['type']
        
        # Handle tables/lists
        if isinstance(seq_content, list):
            seq_content_str = " ".join(" ".join(str(cell) for cell in row) if isinstance(row, list) else str(row) for row in seq_content)
        else:
            seq_content_str = str(seq_content)
        
        print(f"Processing item {i}: {seq_content_str[:50]}...")
        
        # Check if this is a main section header
        if seq_content_str in main_sections_set:
            current_main_section = seq_content_str
            current_subsection = None  # Reset subsection
            if current_main_section not in dic:
                dic[current_main_section] = {}
            print(f"Found main section: {current_main_section}")
            continue
            
        # Check if this is a subsection header (from sections_list)
        if seq_content_str in sections_set:
            if current_main_section:
                current_subsection = seq_content_str
                if current_subsection not in dic[current_main_section]:
                    dic[current_main_section][current_subsection] = {"content": "", "images": {}}
                print(f"Found subsection: {current_subsection}")
            else:
                print(f"Warning: Found subsection '{seq_content_str}' without main section")
            continue
            
        # If we have content that doesn't match any section
        if current_main_section:
            # If no current subsection, create a default one
            if not current_subsection:
                current_subsection = "General Notes"
                if current_subsection not in dic[current_main_section]:
                    dic[current_main_section][current_subsection] = {"content": "", "images": {}}
            
            # Add content to current subsection
            if seq_type == "paragraph":
                # Ensure current_subsection exists in the dictionary
                if current_subsection not in dic[current_main_section]:
                    dic[current_main_section][current_subsection] = {"content": "", "images": {}}
                
                dic[current_main_section][current_subsection]["content"] += seq_content_str + " "
                print(f"Added content to {current_main_section} -> {current_subsection}")
                
            elif seq_type == "image":
                # Ensure current_subsection exists in the dictionary
                if current_subsection not in dic[current_main_section]:
                    dic[current_main_section][current_subsection] = {"content": "", "images": {}}
                
                key = f"IMAGE_{img_count}"
                dic[current_main_section][current_subsection]["content"] += f"[{key}] "
                dic[current_main_section][current_subsection]["images"][key] = seq_content_str
                img_count += 1
                print(f"Added image {key} to {current_main_section} -> {current_subsection}")
        else:
            print(f"Warning: Found content '{seq_content_str[:30]}...' without main section")
    
    # Clean up content (remove extra spaces)
    for main_section in dic:
        for subsection in dic[main_section]:
            if isinstance(dic[main_section][subsection], dict) and "content" in dic[main_section][subsection]:
                dic[main_section][subsection]["content"] = dic[main_section][subsection]["content"].strip()
    
    # Remove empty sections
    cleaned_dic = {}
    for main_section, subsections in dic.items():
        cleaned_subsections = {}
        for subsection, data in subsections.items():
            if isinstance(data, dict) and (data.get("content", "").strip() or data.get("images", {})):
                cleaned_subsections[subsection] = data
        if cleaned_subsections:
            cleaned_dic[main_section] = cleaned_subsections
    
    print(f"Processed {len(cleaned_dic)} main sections with content")
    for main_section, subsections in cleaned_dic.items():
        print(f"  {main_section}: {len(subsections)} subsections")
    
    return cleaned_dic

def validate_parsed_data(parsed_data):
    """
    Validate the structure of parsed data
    
    Args:
        parsed_data: The result from parse_document_sections
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(parsed_data, dict):
        return False
    
    for main_section, subsections in parsed_data.items():
        if not isinstance(subsections, dict):
            return False
        
        for subsection, data in subsections.items():
            if not isinstance(data, dict):
                return False
            
            if "content" not in data or "images" not in data:
                return False
            
            if not isinstance(data["content"], str) or not isinstance(data["images"], dict):
                return False
    
    return True

def get_section_statistics(parsed_data):
    """
    Get statistics about the parsed data
    
    Args:
        parsed_data: The result from parse_document_sections
    
    Returns:
        dict: Statistics about sections, content, and images
    """
    stats = {
        "main_sections": 0,
        "subsections": 0,
        "total_content_length": 0,
        "total_images": 0,
        "sections_with_content": 0,
        "sections_with_images": 0
    }
    
    if not isinstance(parsed_data, dict):
        return stats
    
    stats["main_sections"] = len(parsed_data)
    
    for main_section, subsections in parsed_data.items():
        if isinstance(subsections, dict):
            stats["subsections"] += len(subsections)
            
            for subsection, data in subsections.items():
                if isinstance(data, dict):
                    content = data.get("content", "")
                    images = data.get("images", {})
                    
                    if content:
                        stats["total_content_length"] += len(content)
                        stats["sections_with_content"] += 1
                    
                    if images:
                        stats["total_images"] += len(images)
                        stats["sections_with_images"] += 1
    
    return stats

# Example usage and testing
if __name__ == "__main__":
    # Test sections list
    test_sections = [
        "General Business Overview",
        "General Notes & “Wish List”",
        "Key Value Drivers",
        "Record to Report (R2R)",
        "General Ledger Accounting",
        "Accounts Payable / Receivable"
    ]
    
    # Test JSON data structure
    test_json = {
        "file": {
            "name": "test.docx"
        },
        "sequence": [
            {"type": "table", "content": [["Header1", "Header2"]]},
            {"type": "paragraph", "content": "Record to Report (R2R)"},
            {"type": "paragraph", "content": "General Notes & “Wish List”"},
            {"type": "paragraph", "content": "This is some test content for the section."},
            {"type": "image", "content": "base64imagedata"},
            {"type": "paragraph", "content": "More content here."},
            {"type": "paragraph", "content": "General Ledger Accounting"},
            {"type": "paragraph", "content": "Content for GL accounting section."}
        ]
    }
    
    print("Testing parse_document_sections...")
    result = parse_document_sections(test_sections, test_json)
    
    print("\nResults:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print(f"\nValidation: {validate_parsed_data(result)}")
    
    stats = get_section_statistics(result)
    print(f"\nStatistics: {stats}")