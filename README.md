# Advanced Web Scraper for Clickable Elements

This script provides a powerful tool for identifying and interacting with clickable elements on any webpage. It uses Playwright to automate browser interactions and provides a comprehensive analysis of interactive elements.

## Features

- **Element Detection**: Automatically identifies all clickable elements on a webpage
- **Element Analysis**: Extracts detailed information about each element (tag, text, attributes, position)
- **Visual Highlighting**: Can highlight elements directly on the page
- **Interactive Mode**: Allows you to highlight and click elements interactively
- **Results Export**: Can save analysis results to a JSON file

## Requirements

- Python 3.7+
- Playwright

## Installation

1. Install the required packages:

```bash
pip install playwright
python -m playwright install
```

2. Download the `web_scraper.py` script

## Usage

### Basic Usage

```bash
python web_scraper.py https://www.example.com
```

This will:
1. Open a browser window
2. Navigate to the specified URL
3. Analyze all clickable elements
4. Print the results to the console

### Command Line Options

```
python web_scraper.py [url] [--headless] [--output filename] [--interact]
```

- `url`: The webpage to analyze (default: https://www.example.com)
- `--headless`: Run in headless mode (no browser UI)
- `--output filename`: Save results to a JSON file
- `--interact`: Enter interactive mode after analysis

### Interactive Mode

In interactive mode, you can:

- `h <index>`: Highlight an element by its index
- `c <index>`: Click an element by its index
- `s <index>`: Show detailed information about an element
- `l`: List all elements
- `q`: Quit interactive mode

Example:
```
Enter command: h 5
Highlighted element 5

Enter command: c 5
Clicked element 5
Page navigated to: https://www.newpage.com
```

### Output Format

The JSON output file contains:

```json
{
  "url": "https://www.example.com",
  "title": "Example Domain",
  "timestamp": "2023-06-15 14:30:45",
  "elements": [
    {
      "index": 0,
      "tag_name": "a",
      "text": "More information...",
      "attributes": {
        "href": "https://www.iana.org/domains/example",
        "class": "link"
      },
      "xpath": "/html/body/div/p/a",
      "is_visible": true,
      "is_in_viewport": true,
      "bounding_box": {
        "x": 123.5,
        "y": 456.7,
        "width": 100,
        "height": 20,
        "top": 456.7,
        "right": 223.5,
        "bottom": 476.7,
        "left": 123.5
      }
    },
    // More elements...
  ]
}
```

## How It Works

The script uses a combination of techniques to identify clickable elements:

1. **Tag-based detection**: Identifies common interactive elements like buttons, links, and inputs
2. **Attribute-based detection**: Checks for attributes like `onclick`, `role="button"`, etc.
3. **Event handler detection**: Identifies elements with JavaScript click handlers
4. **Visibility checking**: Ensures elements are visible and not hidden
5. **Position analysis**: Determines if elements are within the viewport

## Examples

### Basic Analysis

```bash
python web_scraper.py https://www.wikipedia.org
```

### Save Results to File

```bash
python web_scraper.py https://www.wikipedia.org --output wikipedia_elements.json
```

### Interactive Mode with Headless Browser

```bash
python web_scraper.py https://www.wikipedia.org --interact --headless
```

## Advanced Usage

You can also import the `WebScraper` class in your own Python scripts:

```python
import asyncio
from web_scraper import WebScraper

async def my_scraping_task():
    async with WebScraper(headless=False) as scraper:
        analysis = await scraper.analyze_page("https://www.example.com")
        
        # Do something with the analysis
        for element in analysis.elements:
            if "login" in element.text.lower():
                await scraper.click_element(element.index, analysis.elements)
                break

asyncio.run(my_scraping_task())
```

## Troubleshooting

- **Element not clickable**: Some elements might be detected as clickable but can't be clicked due to overlays or other elements blocking them
- **Dynamic content**: For pages with dynamic content, you might need to add additional wait times
- **Iframes**: Content inside iframes might not be detected properly
