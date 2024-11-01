# color-ux-access
AI-based UX testing from the perspecive of simulated colorblind web. Powered by Rhymes.ai Aria.

## Process 
- Either Playwright or Selenium launches web browser
- Take screenshot and pass it to computer vision library (OpenCV or alternatives?)
- Apply CV colorblind filters
- Try to follow a workflow
- Ask ARIA image model coordinates to click on
- pass coordinates to automation library and click
- keep going until completing workflow
- Fail the test if ARIA is unable to click 
- Should record video and provide feedback
