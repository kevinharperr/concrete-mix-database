# Concrete Mix Strength Classification Analysis Guide

This guide provides instructions for using the Jupyter notebooks for concrete mix strength analysis and classification.

## Prerequisites

- Python 3.8+ with Jupyter Notebook installed
- Required Python packages: pandas, matplotlib, seaborn, scikit-learn, plotly
- Access to the concrete mix database

## Getting Started

1. Navigate to the project directory in your terminal/command prompt:
   ```
   cd c:/Users/anil_/Documents/concrete_mix_project
   ```

2. Start the Jupyter notebook server:
   ```
   jupyter notebook
   ```

3. In the browser window that opens, navigate to the "analysis" folder and open `strength_classification_analysis.ipynb`

## Using the Notebook

The notebook is organized into sections, each serving a specific purpose in the analysis pipeline. Here's how to use each section:

### 1. Setup and Database Connection

- **Purpose**: Imports libraries and connects to the Django database
- **What to check**: Ensure no errors are shown when importing libraries or connecting to the database
- **Customization**: Modify the Django path if your project is in a different location

### 2. Data Extraction

- **Purpose**: Retrieves concrete mixes with strength test results from the database
- **What to check**: 
  - Number of mixes found with 28-day strength results
  - If limited 28-day data exists, it will suggest other test ages (7, 56, 90, etc.)
- **Customization**: You can modify the `days` parameter in `get_mixes_with_strength_tests(days=28)` to analyze different test ages

### 3. Data Processing

- **Purpose**: Creates a pandas DataFrame from the database data
- **What to check**: 
  - Total number of mixes in the DataFrame
  - First few rows to confirm data was extracted correctly
  - Basic statistics for strength values
- **Customization**: You can add additional fields from your models if needed

### 4. Data Visualization

- **Purpose**: Creates visualizations of strength distribution and relationships with mix components
- **Key visualizations**:
  - Strength distribution histogram
  - Strength vs w/c ratio scatter plot and regression
  - Strength vs material compositions
- **What to check**: 
  - Shape of strength distribution (normal or skewed)
  - Strength-w/c ratio correlation (should be negative per standards)
  - Which materials have strongest correlations with strength
- **Customization**: Add additional plots by copying and modifying existing code cells

### 5. Correlation Analysis

- **Purpose**: Analyzes correlations between all variables
- **What to check**: 
  - Strong positive/negative correlations with strength
  - Relationships between material components
- **Interpretation**: 
  - Values near 1 indicate strong positive correlation
  - Values near -1 indicate strong negative correlation
  - Values near 0 indicate little or no correlation

### 6. Clustering Analysis

- **Purpose**: Groups similar mixes based on composition and identifies patterns
- **Key outputs**:
  - Elbow curve for determining optimal cluster count
  - PCA visualization of clusters
  - Interactive Plotly chart
  - Cluster statistics and composition
- **What to check**:
  - Elbow point on the curve (optimal number of clusters)
  - Separation between clusters in PCA plot
  - Strength differences between clusters
  - Characteristic materials for each cluster
- **Customization**: 
  - Change `n_clusters` value after examining the elbow curve
  - Modify feature selection in `prepare_data_for_clustering()` function

### 7. Results & Export

- **Purpose**: Summarizes findings and exports results to CSV
- **What to check**: Confirm the CSV file was created in the specified location
- **Usage**: The CSV can be used for further analysis or integration into the main application

## Interpreting Results

### Strength Classification

The notebook follows standard concrete classification principles from EN and ASTM standards:

- **EN 206 Classification**: Based primarily on 28-day compressive strength
  - C8/10 through C100/115 classes, where the first number is characteristic cylinder strength and second is cube strength
  
- **ASTM Classification**: Also primarily uses 28-day compressive strength
  - Types based on intended usage (Type I, II, III, etc.)

### Cluster Interpretation

Clusters represent "families" of concrete mixes with similar compositions and strength characteristics:

- **High-Strength Clusters**: Typically have lower w/c ratios and higher cement content
- **Medium-Strength Clusters**: Balanced compositions with moderate w/c ratios
- **Low-Strength Clusters**: Higher w/c ratios, possibly with higher aggregate proportions

## Extending the Analysis

The notebook can be extended in several ways:

1. **Include durability properties** by adding additional dataframe columns
2. **Create predictive models** using scikit-learn regression algorithms
3. **Optimize mix designs** based on target properties
4. **Compare different datasets** by filtering the initial data extraction

## Troubleshooting

- **No data found**: Ensure your database contains performance results with the right category names (contains 'compressive', 'strength', or 'hardened')
- **Error connecting to database**: Verify Django settings and path in the setup section
- **Missing material data**: Check if MixComponent records have the required dosage_kg_m3 values
- **Clustering not showing clear patterns**: Try different feature selections or normalization methods

## References

- European Standard EN 206: Concrete specification, performance, production and conformity
- ASTM C39: Standard Test Method for Compressive Strength of Cylindrical Concrete Specimens
- ACI 318: Building Code Requirements for Structural Concrete
