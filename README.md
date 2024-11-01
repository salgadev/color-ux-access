# color-ux-access
AI-based UX testing from the perspective of simulated colorblind web users. Powered by Rhymes.ai's Aria.

## Getting Started

1. **Clone this repository**
2. **Create a virtual environment**: `python -m venv venv`
3. **Activate the virtual environment**:
	* On Unix or MacOS: `source venv/bin/activate`
	* On Windows: `venv\Scripts\activate`
4. **Install dependencies**: `pip install -r requirements.txt`
5. **Install Playwright browsers**: `playwright install`

## Process
The testing process involves:

1. Launching a web browser using Playwright
2. Taking a screenshot and passing it to a computer vision library (OpenCV or alternatives)
3. Applying a colorblind filter
4. Trying to follow a workflow
5. Asking ARIA image model for coordinates to click on
6. Passing coordinates to an automation library and clicking
7. Continuing until the workflow is complete
8. Failing the test if ARIA is unable to click
9. Recording a video and providing feedback
## Running Tests

Run the entire test suite with:
```
pytest
```

Run a specific test script (must start with 'test') with:

```
pytest test_example.py
```

