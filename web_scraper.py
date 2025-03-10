#!/usr/bin/env python3
"""
Advanced Web Scraper for Identifying and Interacting with Clickable Elements

This script uses Playwright to:
1. Load a webpage
2. Identify all clickable elements
3. Extract their properties (text, attributes, position)
4. Optionally interact with selected elements
5. Save the results to a file

Usage:
    python web_scraper.py [url] [--headless] [--output filename] [--interact]
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser, ElementHandle
except ImportError:
    print("Playwright not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install"])
    from playwright.async_api import async_playwright, Page, Browser, ElementHandle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data classes for representing DOM elements
@dataclass
class ElementInfo:
    """Information about a clickable element on the page"""
    index: int
    tag_name: str
    text: str
    attributes: Dict[str, str] = field(default_factory=dict)
    xpath: str = ""
    is_visible: bool = True
    is_in_viewport: bool = True
    bounding_box: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def __str__(self):
        """String representation of the element"""
        attrs = " ".join([f'{k}="{v}"' for k, v in self.attributes.items() 
                         if k in ['id', 'class', 'name', 'role', 'type', 'href']])
        return f"[{self.index}] <{self.tag_name} {attrs}>{self.text}</{self.tag_name}>"

@dataclass
class PageAnalysis:
    """Analysis results for a webpage"""
    url: str
    title: str
    timestamp: str
    elements: List[ElementInfo] = field(default_factory=list)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "elements": [elem.to_dict() for elem in self.elements]
        }
    
    def save_to_file(self, filename: str):
        """Save analysis results to a JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Analysis saved to {filename}")
    
    def print_elements(self):
        """Print all clickable elements to console"""
        print(f"\n=== Clickable Elements on {self.url} ===")
        print(f"Page Title: {self.title}")
        print(f"Analysis Time: {self.timestamp}")
        print(f"Total Elements: {len(self.elements)}\n")
        
        for elem in self.elements:
            print(elem)

# JavaScript for identifying clickable elements
JS_GET_CLICKABLE_ELEMENTS = """
() => {
    // Helper function to check if element is visible
    function isVisible(element) {
        if (!element.getBoundingClientRect) return false;
        const rect = element.getBoundingClientRect();
        return !!(rect.top || rect.bottom || rect.width || rect.height) && 
               window.getComputedStyle(element).visibility !== 'hidden' &&
               window.getComputedStyle(element).display !== 'none' &&
               window.getComputedStyle(element).opacity !== '0';
    }
    
    // Helper function to check if element is in viewport
    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= -100 &&
            rect.left >= -100 &&
            rect.bottom <= (window.innerHeight + 100) &&
            rect.right <= (window.innerWidth + 100)
        );
    }
    
    // Helper function to check if element is interactive
    function isInteractive(element) {
        const tagName = element.tagName.toLowerCase();
        
        // Common interactive elements
        const interactiveTags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary'];
        if (interactiveTags.includes(tagName)) return true;
        
        // Check for interactive roles
        const role = element.getAttribute('role');
        const interactiveRoles = ['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem'];
        if (role && interactiveRoles.includes(role)) return true;
        
        // Check for event handlers
        if (element.onclick || 
            element.getAttribute('onclick') || 
            element.getAttribute('ng-click') ||
            element.getAttribute('@click')) return true;
        
        // Check for tabindex
        if (element.getAttribute('tabindex') && element.getAttribute('tabindex') !== '-1') return true;
        
        // Check for contenteditable
        if (element.getAttribute('contenteditable') === 'true') return true;
        
        return false;
    }
    
    // Helper function to get all text from an element
    function getElementText(element) {
        // For input elements, get value or placeholder
        if (element.tagName.toLowerCase() === 'input') {
            return element.value || element.placeholder || '';
        }
        
        // For other elements, get innerText or textContent
        return element.innerText || element.textContent || '';
    }
    
    // Helper function to get XPath
    function getXPath(element) {
        if (!element) return '';
        
        // Use id if available
        if (element.id) {
            return `//*[@id="${element.id}"]`;
        }
        
        // Otherwise build path
        const parts = [];
        while (element && element.nodeType === Node.ELEMENT_NODE) {
            let idx = 0;
            let sibling = element.previousSibling;
            while (sibling) {
                if (sibling.nodeType === Node.ELEMENT_NODE && 
                    sibling.tagName === element.tagName) {
                    idx++;
                }
                sibling = sibling.previousSibling;
            }
            
            const tagName = element.tagName.toLowerCase();
            const pathIndex = idx ? `[${idx + 1}]` : '';
            parts.unshift(`${tagName}${pathIndex}`);
            
            element = element.parentNode;
        }
        
        return '/' + parts.join('/');
    }
    
    // Find all clickable elements
    const clickableElements = [];
    let index = 0;
    
    // Function to process elements recursively
    function processElement(element) {
        if (!element || !isVisible(element)) return;
        
        // Check if element is interactive
        if (isInteractive(element)) {
            // Get element properties
            const tagName = element.tagName.toLowerCase();
            const text = getElementText(element).trim();
            const isInView = isInViewport(element);
            const rect = element.getBoundingClientRect();
            
            // Get attributes
            const attributes = {};
            for (const attr of element.attributes) {
                attributes[attr.name] = attr.value;
            }
            
            // Add to results
            clickableElements.push({
                index: index++,
                tagName,
                text: text.substring(0, 100), // Limit text length
                attributes,
                xpath: getXPath(element),
                isVisible: true,
                isInViewport: isInView,
                boundingBox: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    left: rect.left
                }
            });
        }
        
        // Process children
        for (const child of element.children) {
            processElement(child);
        }
    }
    
    // Start processing from body
    processElement(document.body);
    
    return clickableElements;
}
"""

# JavaScript for highlighting elements
JS_HIGHLIGHT_ELEMENT = """
(selector, index) => {
    const element = document.querySelector(selector);
    if (!element) return false;
    
    // Create highlight overlay
    const overlay = document.createElement('div');
    overlay.id = `highlight-overlay-${index}`;
    overlay.style.position = 'absolute';
    overlay.style.border = '2px solid red';
    overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
    overlay.style.zIndex = '10000';
    overlay.style.pointerEvents = 'none';
    
    // Create label
    const label = document.createElement('div');
    label.textContent = index;
    label.style.position = 'absolute';
    label.style.backgroundColor = 'red';
    label.style.color = 'white';
    label.style.padding = '2px 5px';
    label.style.borderRadius = '3px';
    label.style.fontSize = '12px';
    label.style.zIndex = '10001';
    label.style.pointerEvents = 'none';
    
    // Position overlay and label
    const rect = element.getBoundingClientRect();
    overlay.style.top = `${rect.top + window.scrollY}px`;
    overlay.style.left = `${rect.left + window.scrollX}px`;
    overlay.style.width = `${rect.width}px`;
    overlay.style.height = `${rect.height}px`;
    
    label.style.top = `${rect.top + window.scrollY - 20}px`;
    label.style.left = `${rect.left + window.scrollX}px`;
    
    // Add to document
    document.body.appendChild(overlay);
    document.body.appendChild(label);
    
    // Scroll element into view if needed
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    return true;
}
"""

class WebScraper:
    """Advanced web scraper for identifying and interacting with clickable elements"""
    
    def __init__(self, headless: bool = False):
        """Initialize the scraper
        
        Args:
            headless: Whether to run the browser in headless mode
        """
        self.headless = headless
        self.browser = None
        self.page = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def open_page(self, url: str) -> Page:
        """Open a webpage
        
        Args:
            url: The URL to open
            
        Returns:
            The Playwright Page object
        """
        self.page = await self.browser.new_page()
        
        # Set viewport size
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        
        # Navigate to the URL
        logger.info(f"Navigating to {url}")
        await self.page.goto(url, wait_until="networkidle")
        
        # Wait for page to be fully loaded
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)  # Additional wait for dynamic content
        
        return self.page
    
    async def find_clickable_elements(self) -> List[ElementInfo]:
        """Find all clickable elements on the current page
        
        Returns:
            List of ElementInfo objects representing clickable elements
        """
        if not self.page:
            raise ValueError("No page is open. Call open_page() first.")
        
        # Execute JavaScript to find clickable elements
        elements_data = await self.page.evaluate(JS_GET_CLICKABLE_ELEMENTS)
        
        # Convert to ElementInfo objects
        elements = []
        for data in elements_data:
            element = ElementInfo(
                index=data['index'],
                tag_name=data['tagName'],
                text=data['text'],
                attributes=data['attributes'],
                xpath=data['xpath'],
                is_visible=data['isVisible'],
                is_in_viewport=data['isInViewport'],
                bounding_box=data['boundingBox']
            )
            elements.append(element)
        
        logger.info(f"Found {len(elements)} clickable elements")
        return elements
    
    async def analyze_page(self, url: str) -> PageAnalysis:
        """Analyze a webpage to find clickable elements
        
        Args:
            url: The URL to analyze
            
        Returns:
            PageAnalysis object containing the analysis results
        """
        # Open the page
        await self.open_page(url)
        
        # Get page information
        title = await self.page.title()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Find clickable elements
        elements = await self.find_clickable_elements()
        
        # Create and return analysis
        analysis = PageAnalysis(
            url=url,
            title=title,
            timestamp=timestamp,
            elements=elements
        )
        
        return analysis
    
    async def highlight_element(self, element_index: int, elements: List[ElementInfo]) -> bool:
        """Highlight a specific element on the page
        
        Args:
            element_index: The index of the element to highlight
            elements: List of ElementInfo objects
            
        Returns:
            True if the element was highlighted, False otherwise
        """
        if not self.page:
            return False
        
        # Find the element by index
        element = next((e for e in elements if e.index == element_index), None)
        if not element:
            logger.warning(f"Element with index {element_index} not found")
            return False
        
        # Create a CSS selector from the element's attributes
        selector = None
        if 'id' in element.attributes:
            selector = f"#{element.attributes['id']}"
        elif element.xpath:
            # Use JavaScript to find element by XPath
            selector = await self.page.evaluate(f"""
                xpath => {{
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    return result.singleNodeValue ? true : false;
                }}
            """, element.xpath)
            if selector:
                # If XPath is valid, use it with page.evaluate
                await self.page.evaluate(f"""
                    xpath => {{
                        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        const element = result.singleNodeValue;
                        if (element) {{
                            element.style.border = '2px solid red';
                            element.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        }}
                    }}
                """, element.xpath)
                return True
            return False
        
        # If we have a CSS selector, use it
        if selector:
            result = await self.page.evaluate(JS_HIGHLIGHT_ELEMENT, selector, element_index)
            return result
        
        return False
    
    async def click_element(self, element_index: int, elements: List[ElementInfo]) -> bool:
        """Click on a specific element
        
        Args:
            element_index: The index of the element to click
            elements: List of ElementInfo objects
            
        Returns:
            True if the element was clicked, False otherwise
        """
        if not self.page:
            return False
        
        # Find the element by index
        element = next((e for e in elements if e.index == element_index), None)
        if not element:
            logger.warning(f"Element with index {element_index} not found")
            return False
        
        try:
            # Try to click using XPath
            if element.xpath:
                await self.page.click(f"xpath={element.xpath}")
                logger.info(f"Clicked element {element_index} using XPath")
                return True
            
            # Try to click using CSS selector if ID is available
            if 'id' in element.attributes:
                await self.page.click(f"#{element.attributes['id']}")
                logger.info(f"Clicked element {element_index} using ID selector")
                return True
            
            # Try to click using coordinates
            if element.bounding_box:
                x = element.bounding_box['x'] + element.bounding_box['width'] / 2
                y = element.bounding_box['y'] + element.bounding_box['height'] / 2
                await self.page.mouse.click(x, y)
                logger.info(f"Clicked element {element_index} using coordinates")
                return True
            
            logger.warning(f"Could not click element {element_index}")
            return False
        except Exception as e:
            logger.error(f"Error clicking element {element_index}: {e}")
            return False
    
    async def interactive_mode(self, elements: List[ElementInfo]) -> None:
        """Enter interactive mode to highlight and click elements
        
        Args:
            elements: List of ElementInfo objects
        """
        print("\n=== Interactive Mode ===")
        print("Commands:")
        print("  h <index> - Highlight element")
        print("  c <index> - Click element")
        print("  s <index> - Show element details")
        print("  l - List all elements")
        print("  q - Quit interactive mode")
        
        while True:
            command = input("\nEnter command: ").strip()
            
            if command.lower() == 'q':
                break
            
            if command.lower() == 'l':
                for element in elements:
                    print(element)
                continue
            
            parts = command.split()
            if len(parts) != 2:
                print("Invalid command format. Use 'h <index>', 'c <index>', or 's <index>'")
                continue
            
            action, index_str = parts
            try:
                index = int(index_str)
            except ValueError:
                print(f"Invalid index: {index_str}")
                continue
            
            element = next((e for e in elements if e.index == index), None)
            if not element:
                print(f"Element with index {index} not found")
                continue
            
            if action.lower() == 'h':
                await self.highlight_element(index, elements)
                print(f"Highlighted element {index}")
            
            elif action.lower() == 'c':
                result = await self.click_element(index, elements)
                if result:
                    print(f"Clicked element {index}")
                    # Wait for page to load after click
                    await self.page.wait_for_load_state("networkidle")
                    # Re-analyze page if it changed
                    new_url = self.page.url
                    print(f"Page navigated to: {new_url}")
                else:
                    print(f"Failed to click element {index}")
            
            elif action.lower() == 's':
                print("\nElement Details:")
                print(f"  Index: {element.index}")
                print(f"  Tag: {element.tag_name}")
                print(f"  Text: {element.text}")
                print(f"  XPath: {element.xpath}")
                print(f"  Attributes:")
                for k, v in element.attributes.items():
                    print(f"    {k}: {v}")
                print(f"  Bounding Box:")
                for k, v in element.bounding_box.items():
                    print(f"    {k}: {v}")
            
            else:
                print(f"Unknown action: {action}")

async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Web Scraper for Clickable Elements")
    parser.add_argument("url", nargs="?", default="https://www.google.com", 
                        help="URL to scrape (default: https://www.google.com)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    parser.add_argument("--interact", action="store_true", help="Enter interactive mode")
    args = parser.parse_args()
    
    # Create and run scraper
    async with WebScraper(headless=args.headless) as scraper:
        # Analyze page
        analysis = await scraper.analyze_page(args.url)
        
        # Print results
        analysis.print_elements()
        
        # Save results if output file specified
        if args.output:
            analysis.save_to_file(args.output)
        
        # Enter interactive mode if requested
        if args.interact:
            await scraper.interactive_mode(analysis.elements)

if __name__ == "__main__":
    asyncio.run(main())
