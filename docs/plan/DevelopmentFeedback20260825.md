# Development Feedback 20260825

**Dependancy Upgrades**
- Upgrade backend to use httpx2

**Exported Excel Display**
- Follow the golden file (sample_data\expected_output\output_13_19_Jul26.xlsx) data display on exported excel. Show all product groups, variants and value. If the raw inputs for specific product groups or variants are not available, set the value to 0.

**Dashboard Display**
- Redesign the dashboard to show batch selector, display Contribution Pie chart and Product sales bar chart for selected batch.
- Show data list for selected batch, the selected batch can have 3 checkboxes for showing : 
  - Single Data
  - Bundling Data
  - Cross Bundling Data
